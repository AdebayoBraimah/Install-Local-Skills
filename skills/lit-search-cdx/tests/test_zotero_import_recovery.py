from concurrent.futures import ThreadPoolExecutor
from litsearch.state import State, Blocked
from litsearch.zotero_import import Importer
from test_zotero_import import FakeZotero
from test_acquisition import record, make_pdf


def test_lost_upload_response_reconciles_stored_pdf(tmp_path):
    class LostUpload(FakeZotero):
        def upload(self, key, path):
            super().upload(key, path)
            raise Blocked("zotero_timeout_or_unavailable")

    api = LostUpload()
    r = record()
    pdf = tmp_path / "paper.pdf"
    make_pdf(pdf, r["title"])
    r["download"] = {"path": str(pdf)}
    first = Importer(State(tmp_path / "state"), api).run(
        "first", [r], [r["id"]], "Review", approved=True
    )
    assert first["status"] == "partial"
    second = Importer(State(tmp_path / "state"), api).run(
        "resume", [r], [r["id"]], "Review", approved=True
    )
    assert second["status"] == "complete"
    assert second["records"][0]["zotero_import"]["attachment"]["status"] == "present"
    assert len(api.objects["items"]) == 2
    assert sum(w[0] == "upload" for w in api.writes) == 1


def test_two_runs_serialize_parent_creation(tmp_path):
    api = FakeZotero()
    r = record()

    def run(name):
        return Importer(State(tmp_path), api).run(
            name, [r], [r["id"]], "Review", approved=True
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, ["first", "second"]))
    keys = {out["records"][0]["zotero_import"]["item_key"] for out in results}
    assert len(keys) == 1 and len(api.objects["items"]) == 1
