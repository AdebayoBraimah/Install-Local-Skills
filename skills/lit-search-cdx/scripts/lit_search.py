#!/Users/adebayobraimah/anaconda3/bin/python
"""Shared academic acquisition CLI. JSON stdout on success and failure."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import uuid
from litsearch.auth import Credentials
from litsearch.state import State, Blocked, digest
from litsearch.providers import Providers
from litsearch.workflow import Workflow, report
from litsearch.acquisition import fetch, bundle


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def parser():
    p = Parser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    for name in (
        "search",
        "citations",
        "versions",
        "enrich",
        "fetch",
        "bundle",
        "import",
        "doctor",
        "auth",
    ):
        s = sub.add_parser(name)
        s.add_argument("--state-dir")
        s.add_argument("--fixture")
        s.add_argument("--run-id", default=os.environ.get("LIT_SEARCH_RUN_ID"))
        s.add_argument("--output")
        s.add_argument("--report")
        if name in ("search", "citations", "versions", "enrich"):
            s.add_argument("--refresh", action="store_true")
        if name == "search":
            s.add_argument("query")
        if name in ("citations", "versions"):
            s.add_argument("seed")
        if name in ("search", "citations"):
            s.add_argument(
                "--provider", choices=["scholar", "openalex"], default="scholar"
            )
        if name in ("search", "citations", "versions"):
            s.add_argument("--limit", type=int, default=20)
        if name == "citations":
            s.add_argument(
                "--direction", choices=["forward", "backward"], default="forward"
            )
        if name in ("enrich", "fetch", "bundle", "import"):
            s.add_argument("--input", required=True)
        if name in ("fetch", "bundle", "import"):
            s.add_argument("--select", nargs="+", required=True)
        if name == "import":
            s.add_argument("--collection", required=True)
            s.add_argument("--create-collection", action="store_true")
            approval = s.add_mutually_exclusive_group(required=True)
            approval.add_argument("--dry-run", action="store_true")
            approval.add_argument("--selection-approved", action="store_true")
        if name == "enrich":
            s.add_argument("--cite-export", action="store_true")
        if name == "auth":
            s.add_argument("action", choices=["status", "import"])
        if name == "doctor":
            s.add_argument("--live", action="store_true")
    return p


class FixtureHTTP:
    def __init__(self, data):
        self.data = data

    def get(self, url, **kwargs):
        if url.endswith("/me"):
            payload = self.data["account"]
            status = 200
            headers = {}
        else:
            row = next(
                (
                    r
                    for r in self.data.get("responses", [])
                    if r.get("params", {}) == kwargs.get("params", {})
                    and (not r.get("url") or r["url"] == url)
                ),
                None,
            )
            if row is None:
                raise Blocked("fixture_request_missing")
            payload = row["data"]
            status = row.get("status", 200)
            headers = row.get("headers", {})

        class Response:
            status_code = status

            def json(self):
                return payload

        response = Response()
        response.headers = headers
        return response


class FixtureCredentials:
    def get_password(self, service, account):
        return "fixture-key" if account == "searchapi" else None


def build(state_dir=None, fixture=None):
    if fixture:
        if not state_dir:
            raise ValueError("fixtures require an isolated --state-dir")
        data = json.loads(Path(fixture).read_text())
        state = State(state_dir, clock=lambda: float(data.get("clock", 1789084800)))
        provider = Providers(
            state,
            Credentials(backend=FixtureCredentials()),
            FixtureHTTP(data),
            sleep=lambda _: None,
        )
        import litsearch.acquisition as acquisition

        acquisition.zotero = lambda *args: data.get("zotero", {}).get(
            json.dumps(args), []
        )

        def fixture_download(url, **kwargs):
            path = data.get("downloads", {}).get(url)
            if not path:
                raise Blocked("fixture_download_missing")
            return Path(path).read_bytes(), url

        acquisition.download_bytes = fixture_download
        return provider
    return Providers(State(state_dir), Credentials())


def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main(argv=None):
    auth = None
    args = None
    run = None
    try:
        args = parser().parse_args(argv)
        run = args.run_id or "standalone-" + str(uuid.uuid4())
        if args.command == "import" and args.fixture:
            raise Blocked("fixture_import_not_supported_use_injected_test_transport")
        p = build(args.state_dir, args.fixture)
        auth = p.auth
        w = Workflow(p)
        if args.command == "auth":
            result = (
                auth.import_file()
                if args.action == "import"
                else {"status": "complete", "credentials": auth.status()}
            )
        elif args.command == "doctor":
            deps = {x: bool(shutil.which(x)) for x in ("pdfinfo", "pdftotext")}
            result = {
                "status": "complete" if all(deps.values()) else "blocked",
                "dependencies": deps,
                "credentials": auth.status(),
                "state": str(p.state.root),
                "usage": p.state.usage(run),
            }
            if args.live:
                try:
                    result["searchapi_account"] = p.account(
                        "searchapi", p.credential("searchapi"), 1
                    )
                except Blocked as e:
                    result["searchapi_account"] = {"reason": e.code}
                    result["status"] = "blocked"
                try:
                    result["openalex_budget"] = p.account(
                        "openalex", p.credential("openalex"), 1
                    )
                except Blocked as e:
                    result["openalex_budget"] = {"reason": e.code}
        elif args.command == "search":
            result = w.search(run, args.query, args.provider, args.limit, args.refresh)
        elif args.command == "versions":
            result = w.versions(run, args.seed, args.limit, args.refresh)
        elif args.command == "citations":
            result = w.citations(
                run, args.seed, args.provider, args.direction, args.limit, args.refresh
            )
        else:
            data = json.loads(Path(args.input).read_text())
            records = data.get("records", []) if isinstance(data, dict) else data
            if not isinstance(records, list) or any(
                not isinstance(r, dict) or not r.get("id") or not r.get("title")
                for r in records
            ):
                raise ValueError(
                    "input must contain normalized records with id and title"
                )
            if args.command == "enrich":
                result = w.enrich(run, records, args.refresh, args.cite_export)
            elif args.command == "fetch":
                result = fetch(p, run, records, args.select)
            elif args.command == "import":
                from litsearch.zotero_import import Importer
                from litsearch.zotero_transport import LocalZotero

                result = Importer(p.state, LocalZotero()).run(
                    run,
                    records,
                    args.select,
                    args.collection,
                    approved=args.selection_approved,
                    dry_run=args.dry_run,
                    create_collection=args.create_collection,
                )
            else:
                result = bundle(p.state, run, records, args.select)
        result = auth.clean(result)
        result.setdefault("run_id", run)
        text = json.dumps(result, indent=2)
        if args.output:
            atomic_write(args.output, text + "\n")
        if args.report:
            result.setdefault("records", [])
            atomic_write(args.report, report(result))
        if args.command not in ("doctor", "auth"):
            atomic_write(
                p.state.root
                / "runs"
                / digest(run)[:20]
                / ("last-" + args.command + ".json"),
                text + "\n",
            )
        print(text)
        return {"complete": 0, "partial": 2, "blocked": 3, "failed": 1}[
            result["status"]
        ]
    except (Blocked, ValueError, OSError, KeyError, TypeError) as e:
        result = {
            "status": "blocked" if isinstance(e, Blocked) else "failed",
            "run_id": run,
            "records": [],
            "remaining_work": [
                {
                    "reason": (
                        e.code
                        if isinstance(e, Blocked)
                        else "invalid_input_or_local_io"
                    )
                }
            ],
        }
        print(json.dumps(result))
        return 3 if isinstance(e, Blocked) else 1


if __name__ == "__main__":
    sys.exit(main())
