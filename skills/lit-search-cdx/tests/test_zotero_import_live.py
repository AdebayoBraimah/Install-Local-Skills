"""Opt-in synthetic integration test; cleans only keys created in its private journal."""

import json
import os
import uuid
from pathlib import Path
import pytest
from litsearch.state import State
from litsearch.records import base
from litsearch.zotero_import import Importer
from litsearch.zotero_transport import LocalZotero
from test_acquisition import make_pdf


@pytest.mark.skipif(
    os.environ.get("LITSEARCH_LIVE_ZOTERO") != "1",
    reason="explicit live test opt-in required",
)
def test_synthetic_import_repeat_and_cleanup(tmp_path):
    api = LocalZotero()
    state = State(tmp_path / "state")
    token = uuid.uuid4().hex
    title = "Synthetic import verification " + token
    collection = "lit-search-import-test-" + token
    r = base(title, "synthetic-test", {"id": token}, {})
    r.update(authors=["Synthetic Researcher"], year=2026)
    pdf = tmp_path / "source.pdf"
    make_pdf(pdf, title)
    r["download"] = {"status": "verified", "path": str(pdf)}
    importer = Importer(state, api)
    cleanup = []
    try:
        dry = importer.run(
            "live", [r], [r["id"]], collection, dry_run=True, create_collection=True
        )
        assert dry["records"][0]["zotero_import"]["action"] == "would_create"
        first = importer.run(
            "live", [r], [r["id"]], collection, approved=True, create_collection=True
        )
        assert first["status"] == "complete", first["remaining_work"]
        first_info = first["records"][0]["zotero_import"]
        second = importer.run("live-resume", [r], [r["id"]], collection, approved=True)
        second_info = second["records"][0]["zotero_import"]
        assert second["status"] == "complete", second["remaining_work"]
        assert second_info["item_key"] == first_info["item_key"]
        assert second_info["attachment"]["key"] == first_info["attachment"]["key"]
        assert second_info["attachment"]["status"] == "present"
        assert (
            Path(api.file(first_info["attachment"]["key"])).read_bytes()
            == pdf.read_bytes()
        )
        parents = [x for x in api.all("items") if x.get("title") == title]
        assert len(parents) == 1
        children = [
            x for x in api.all("items") if x.get("parentItem") == first_info["item_key"]
        ]
        assert len(children) == 1
    finally:
        with state.db() as db:
            try:
                entries = [
                    (key, json.loads(data))
                    for key, data in db.execute(
                        "SELECT identity,data FROM zotero_imports"
                    )
                ]
            except Exception:
                entries = []
        for ident, entry in entries:
            if not entry.get("key") and entry.get("marker"):
                kind = "collections" if ident.startswith("collection:") else "items"
                matches = [
                    row
                    for row in api.all(kind)
                    if any(
                        entry["marker"] in str(row.get(field, ""))
                        for field in ("extra", "note", "name")
                    )
                ]
                assert len(matches) <= 1, "ambiguous synthetic cleanup marker"
                if matches:
                    entry["key"] = matches[0]["key"]
        entries = [(ident, entry) for ident, entry in entries if entry.get("key")]
        entries.sort(
            key=lambda x: (
                0
                if x[0].startswith("attachment:")
                else 1 if x[0].startswith("parent:") else 2
            )
        )
        parent_keys = {
            e["key"]
            for ident, e in entries
            if ident.startswith("parent:") and e["payload"].get("title") == title
        }
        for ident, entry in entries:
            kind = "collections" if ident.startswith("collection:") else "items"
            row = api.get(kind, entry["key"])
            if not row:
                continue
            owned = (
                (
                    kind == "collections"
                    and row.get("name") in (collection, entry["payload"].get("name"))
                )
                or (entry["key"] in parent_keys and row.get("title") == title)
                or (
                    ident.startswith("attachment:")
                    and row.get("parentItem") in parent_keys
                )
            )
            assert owned, "cleanup ownership guard failed"
            api.call(
                "DELETE",
                "/api/users/0/" + kind + "/" + entry["key"],
                headers={"If-Unmodified-Since-Version": str(row["version"])},
            )
            assert api.get(kind, entry["key"]) is None
            cleanup.append(entry["key"])
        print("Synthetic objects deleted:", len(cleanup))
