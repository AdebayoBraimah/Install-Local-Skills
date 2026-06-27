from __future__ import annotations

import json
from pathlib import Path

from obsidian_graphrag.config import GraphRAGConfig
from validate_graphrag import scan_for_tracked_secrets, validate_input


def test_validate_input_accepts_required_document_schema(tmp_path: Path) -> None:
    path = tmp_path / "obsidian_graphrag_input.json"
    metadata = {
        "source_path": "Ideas/note.md",
        "sha256": "abc",
        "mtime_ns": 1,
        "tags": [],
        "aliases": [],
        "keywords": [],
        "category": None,
        "wikilinks": [],
        "image_refs": [],
        "sidecar_paths": [],
        "warning_count": 0,
    }
    path.write_text(
        json.dumps([{"id": "note:abc", "title": "Note", "text": "Body", "metadata": metadata, **metadata}]),
        encoding="utf-8",
    )

    result = validate_input(path)

    assert result["errors"] == []
    assert result["document_count"] == 1


def test_secret_scan_flags_real_key_but_not_example(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir()
    (tmp_path / ".env.example").write_text("GRAPHRAG_API_KEY=replace-with-rotated-key\n", encoding="utf-8")
    fake_prefix = "s" + "k" + "-"
    (tmp_path / "config" / "bad.txt").write_text(
        f"GRAPHRAG_API_KEY={fake_prefix}testsecret1234567890\n",
        encoding="utf-8",
    )

    findings = scan_for_tracked_secrets(tmp_path)

    assert len(findings) == 1
    assert "bad.txt" in findings[0]
