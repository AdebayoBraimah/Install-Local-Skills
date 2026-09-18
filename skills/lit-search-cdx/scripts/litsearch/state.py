"""Shared conservative spending ledger and durable per-run completion."""

import contextlib
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time


class Blocked(Exception):
    def __init__(self, code, details=None):
        self.code, self.details = code, details or {}
        super().__init__(code)


def stamp(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class State:
    def __init__(self, root=None, clock=time.time):
        self.root = Path(root or Path.home() / ".local/share/lit-search-cdx")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.clock = clock
        self.path = self.root / "ledger.sqlite3"
        with self.db() as db:
            db.executescript(
                """
            CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY, provider TEXT, run TEXT, time REAL, units INTEGER, outcome TEXT);
            CREATE TABLE IF NOT EXISTS daily(provider TEXT, period TEXT, day TEXT, allowance INTEGER, PRIMARY KEY(provider,period,day));
            CREATE TABLE IF NOT EXISTS steps(run TEXT, key TEXT, data TEXT, PRIMARY KEY(run,key));
            CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY, time REAL, data TEXT);
            CREATE TABLE IF NOT EXISTS holds(provider TEXT PRIMARY KEY, until REAL);
            """
            )
        os.chmod(self.path, 0o600)

    @contextlib.contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=60)
        try:
            db.execute("PRAGMA busy_timeout=60000")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def reserve(self, provider, run, account, units=1):
        # Account observation and reservation share a write transaction. All local
        # attempts remain charged, even after failure or process death.
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            now = self.clock()
            day = dt.datetime.fromtimestamp(now, dt.timezone.utc).date().isoformat()
            hold = db.execute(
                "SELECT until FROM holds WHERE provider=?", (provider,)
            ).fetchone()
            if hold and hold[0] > now:
                raise Blocked("rate_limited", {"retry_at": hold[0]})
            info = account()
            if provider == "searchapi":
                try:
                    a = info["account"]
                    sub = info["subscription"]
                    h = info["api_usage"]
                    start, end = stamp(sub["period_start"]), stamp(sub["period_end"])
                    if not start <= now < end:
                        raise ValueError()
                    remaining = min(
                        int(a["remaining_credits"]),
                        min(10000, int(a["monthly_allowance"]))
                        - int(a["current_month_usage"]),
                    )
                    hourly = max(
                        0, int(h["hourly_rate_limit"]) - int(h["searches_this_hour"])
                    )
                except (KeyError, ValueError, TypeError, AttributeError):
                    raise Blocked("billing_information_unavailable") from None
                period = sub["period_start"]
                total = db.execute(
                    "SELECT COALESCE(SUM(units),0) FROM attempts WHERE provider=? AND time>=?",
                    (provider, start),
                ).fetchone()[0]
                run_total = db.execute(
                    "SELECT COUNT(*) FROM attempts WHERE provider=? AND run=?",
                    (provider, run),
                ).fetchone()[0]
                hour_total = db.execute(
                    "SELECT COUNT(*) FROM attempts WHERE provider=? AND time>=?",
                    (provider, now - 3600),
                ).fetchone()[0]
                if run_total >= 100:
                    raise Blocked("run_quota", {"used": run_total})
                if hour_total >= hourly:
                    raise Blocked("hourly_quota")
                available = max(0, remaining - total)
                # End is exclusive, so midnight end does not add another date.
                dates = (
                    dt.datetime.fromtimestamp(end - 0.000001, dt.timezone.utc).date()
                    - dt.date.fromisoformat(day)
                ).days + 1
                allowance = available // max(1, dates)
            else:
                start = stamp(day + "T00:00:00Z")
                period = day
                total = db.execute(
                    "SELECT COALESCE(SUM(units),0) FROM attempts WHERE provider=? AND time>=?",
                    (provider, start),
                ).fetchone()[0]
                if units == 0:
                    available = 10**12
                    allowance = 10**12
                else:
                    available = max(0, int(info["free_remaining"]) - total)
                    allowance = int(info["free_limit"])
            row = db.execute(
                "SELECT allowance FROM daily WHERE provider=? AND period=? AND day=?",
                (provider, period, day),
            ).fetchone()
            if row:
                allowance = row[0]
            else:
                db.execute(
                    "INSERT INTO daily VALUES(?,?,?,?)",
                    (provider, period, day, allowance),
                )
            today = db.execute(
                "SELECT COALESCE(SUM(units),0) FROM attempts WHERE provider=? AND time>=?",
                (provider, stamp(day + "T00:00:00Z")),
            ).fetchone()[0]
            if units > available or today + units > allowance:
                raise Blocked(
                    "daily_or_account_quota",
                    {
                        "daily_allowance": allowance,
                        "used_today": today,
                        "available": available,
                    },
                )
            return db.execute(
                "INSERT INTO attempts(provider,run,time,units,outcome) VALUES(?,?,?,?,?)",
                (provider, run, now, units, "uncertain"),
            ).lastrowid

    def finish(self, attempt, outcome):
        with self.db() as db:
            db.execute("UPDATE attempts SET outcome=? WHERE id=?", (outcome, attempt))

    def hold(self, provider, seconds):
        with self.db() as db:
            db.execute(
                "INSERT INTO holds VALUES(?,?) ON CONFLICT(provider) DO UPDATE SET until=MAX(until,excluded.until)",
                (provider, self.clock() + seconds),
            )

    def get(self, run, key, refresh=False):
        if refresh:
            return None
        with self.db() as db:
            row = db.execute(
                "SELECT data FROM steps WHERE run=? AND key=?", (run, key)
            ).fetchone()
            if row:
                return json.loads(row[0])
            row = db.execute(
                "SELECT data FROM cache WHERE key=? AND time>?",
                (key, self.clock() - 7 * 86400),
            ).fetchone()
            if row:
                db.execute(
                    "INSERT OR REPLACE INTO steps VALUES(?,?,?)", (run, key, row[0])
                )
                return json.loads(row[0])

    def put(self, run, key, data):
        payload = json.dumps(data)
        with self.db() as db:
            db.execute(
                "INSERT OR REPLACE INTO steps VALUES(?,?,?)", (run, key, payload)
            )
            db.execute(
                "INSERT OR REPLACE INTO cache VALUES(?,?,?)",
                (key, self.clock(), payload),
            )

    @contextlib.contextmanager
    def request_lock(self, key):
        import fcntl

        directory = self.root / "locks"
        directory.mkdir(exist_ok=True)
        with (directory / digest(key)).open("a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def usage(self, run):
        with self.db() as db:
            return {
                "attempts": [
                    {"provider": r[0], "requests": r[1], "units": r[2]}
                    for r in db.execute(
                        "SELECT provider,COUNT(*),SUM(units) FROM attempts WHERE run=? GROUP BY provider",
                        (run,),
                    )
                ],
                "completed_steps": [
                    r[0]
                    for r in db.execute("SELECT key FROM steps WHERE run=?", (run,))
                ],
            }
