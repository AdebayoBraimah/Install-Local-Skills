import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from litsearch.state import State, Blocked

NOW = 1789084800.0  # 2026-09-11 UTC


def account(remaining=100):
    return {
        "account": {
            "remaining_credits": remaining,
            "monthly_allowance": 10000,
            "current_month_usage": 0,
        },
        "api_usage": {"searches_this_hour": 0, "hourly_rate_limit": 100},
        "subscription": {
            "period_start": "2026-09-01T00:00:00Z",
            "period_end": "2026-09-21T00:00:00Z",
        },
    }


def test_concurrent_daily_reservations_are_shared(tmp_path):
    s = State(tmp_path, clock=lambda: NOW)

    def attempt(i):
        try:
            return s.reserve("searchapi", str(i), lambda: account(), 1)
        except Blocked:
            return None

    with ThreadPoolExecutor(max_workers=16) as pool:
        ids = list(pool.map(attempt, range(30)))
    assert sum(x is not None for x in ids) == 10
    with pytest.raises(Blocked):
        State(tmp_path, clock=lambda: NOW).reserve(
            "searchapi", "new", lambda: account(), 1
        )


def test_resume_outlives_cache_and_refresh(tmp_path):
    clock = [NOW]
    s = State(tmp_path, clock=lambda: clock[0])
    s.put("parent", "query", {"records": [1]})
    clock[0] += 8 * 86400
    assert s.get("parent", "query") == {"records": [1]}
    assert s.get("new", "query") is None
    assert s.get("parent", "query", refresh=True) is None


def test_run_cap_survives_rollover_and_failures(tmp_path):
    clock = [NOW]
    s = State(tmp_path, clock=lambda: clock[0])
    a = account(10000)
    a["api_usage"]["hourly_rate_limit"] = 10000
    for i in range(100):
        rid = s.reserve("searchapi", "parent", lambda: a)
        s.finish(rid, "timeout")
    clock[0] += 30 * 86400
    a["subscription"] = {
        "period_start": "2026-10-01T00:00:00Z",
        "period_end": "2026-10-21T00:00:00Z",
    }
    with pytest.raises(Blocked, match="run_quota"):
        s.reserve("searchapi", "parent", lambda: a)


def test_external_usage_tightens_and_missing_period_blocks(tmp_path):
    s = State(tmp_path, clock=lambda: NOW)
    s.reserve("searchapi", "p", lambda: account())
    with pytest.raises(Blocked):
        s.reserve("searchapi", "q", lambda: account(0))
    a = account()
    a.pop("subscription")
    with pytest.raises(Blocked, match="billing_information"):
        s.reserve("searchapi", "q", lambda: a)


def test_next_day_carries_unused_and_frozen_budget(tmp_path):
    clock = [NOW]
    s = State(tmp_path, clock=lambda: clock[0])
    s.reserve("searchapi", "r", lambda: account(100))
    # A larger balance does not reset today's allocation of 10.
    for i in range(9):
        s.reserve("searchapi", "r", lambda: account(200))
    with pytest.raises(Blocked):
        s.reserve("searchapi", "r", lambda: account(200))
    clock[0] += 86400
    assert s.reserve("searchapi", "r", lambda: account(200))


def test_openalex_free_cap_and_anonymous_content(tmp_path):
    s = State(tmp_path, clock=lambda: NOW)
    free = {"free_limit": 1000, "free_remaining": 1000}
    for _ in range(10):
        s.reserve("openalex", "r", lambda: free, 100)
    with pytest.raises(Blocked):
        s.reserve("openalex", "new", lambda: free, 1)
    assert s.reserve("openalex", "r", lambda: {}, 0)


def test_exclusive_midnight_end_and_pending_charged(tmp_path):
    s = State(tmp_path, clock=lambda: NOW)
    a = account(1)
    a["subscription"]["period_end"] = "2026-09-12T00:00:00Z"
    s.reserve("searchapi", "r", lambda: a)
    with pytest.raises(Blocked):
        State(tmp_path, clock=lambda: NOW).reserve("searchapi", "other", lambda: a)
