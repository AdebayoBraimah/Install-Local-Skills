from __future__ import annotations

import json

from obsidian_llamaindex_rag.discover import FileRecord
from obsidian_llamaindex_rag.manifest import diff_records, empty_manifest, manifest_entry, write_manifest_atomic


def record(path="a.md", size=1, modified_time=10, content_hash="hash"):
    return FileRecord(
        path=None,
        relative_path=path,
        size=size,
        modified_time=modified_time,
        content_hash=content_hash,
    )


def test_diff_records_detects_changed_deleted_and_unchanged():
    manifest = empty_manifest("collection")
    manifest["files"] = {
        "a.md": manifest_entry(record("a.md"), ["chunk-a"]),
        "b.md": manifest_entry(record("b.md"), ["chunk-b"]),
        "deleted.md": manifest_entry(record("deleted.md"), ["chunk-c"]),
    }

    changed, deleted, unchanged = diff_records(
        [record("a.md"), record("b.md", modified_time=11)],
        manifest,
    )

    assert [item.relative_path for item in changed] == ["b.md"]
    assert deleted == ["deleted.md"]
    assert [item.relative_path for item in unchanged] == ["a.md"]


def test_write_manifest_atomic_replaces_file(tmp_path):
    path = tmp_path / "manifest.json"
    manifest = empty_manifest("collection")
    manifest["files"]["a.md"] = manifest_entry(record("a.md"), ["chunk"])

    write_manifest_atomic(path, manifest)

    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["files"]["a.md"]["chunk_ids"] == ["chunk"]
    assert loaded["generated_at"]
    assert not list(tmp_path.glob("*.tmp"))

