from __future__ import annotations

import logging
from datetime import date

from obsidian_llamaindex_rag.chunking import chunk_markdown_file, normalize_frontmatter, split_frontmatter
from obsidian_llamaindex_rag.config import load_config
from obsidian_llamaindex_rag.discover import FileRecord

from .test_config import write_config


def test_frontmatter_normalization_keeps_allowed_scalar_and_list_values(caplog):
    caplog.set_level(logging.WARNING)
    normalized = normalize_frontmatter(
        {
            "Title": "Paper",
            "Medium": 2026,
            "Category": {"nested": "drop"},
            "Date Created": date(2026, 6, 15),
            "tags": ["rag", 2, {"drop": True}],
            "Keywords": "retrieval",
            "Extra": "ignored",
        },
        "note.md",
    )

    assert normalized == {
        "Title": "Paper",
        "Medium": "2026",
        "Date Created": "2026-06-15",
        "tags": "rag, 2",
        "Keywords": "retrieval",
    }
    assert "Dropping nested" in caplog.text


def test_malformed_frontmatter_logs_warning_and_continues(caplog):
    caplog.set_level(logging.WARNING)
    frontmatter, body = split_frontmatter("---\nTitle: [bad\n---\n# Body\n", source_path="bad.md")

    assert frontmatter == {}
    assert body == "# Body\n"
    assert "Malformed YAML frontmatter" in caplog.text


def test_chunk_markdown_file_adds_heading_and_metadata(tmp_path):
    rag_dir = tmp_path / ".vault-llamaindex-rag"
    rag_dir.mkdir()
    write_config(rag_dir / "config.yaml", chunk_size=20, chunk_overlap=5)
    note = tmp_path / "Ideas" / "note.md"
    note.parent.mkdir()
    note.write_text(
        "---\nTitle: Test Note\ntags: [alpha, beta]\n---\n"
        "# Main\n\n"
        "First section text.\n\n"
        "## Child\n\n"
        "Second section text.\n",
        encoding="utf-8",
    )
    stat = note.stat()
    record = FileRecord(
        path=note,
        relative_path="Ideas/note.md",
        size=stat.st_size,
        modified_time=stat.st_mtime_ns,
        content_hash="abc123",
    )
    config = load_config(rag_dir / "config.yaml")

    chunks = chunk_markdown_file(record, config, use_llama_parser=False)

    assert chunks
    assert chunks[0].metadata["source_path"] == "Ideas/note.md"
    assert chunks[0].metadata["Title"] == "Test Note"
    assert chunks[0].metadata["tags"] == "alpha, beta"
    assert any(chunk.metadata["heading"] == "Main / Child" for chunk in chunks)
    assert all(chunk.metadata["chunk_id"] == chunk.chunk_id for chunk in chunks)
