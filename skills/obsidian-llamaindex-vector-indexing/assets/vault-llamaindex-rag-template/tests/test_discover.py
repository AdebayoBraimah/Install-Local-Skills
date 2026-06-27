from __future__ import annotations

from obsidian_llamaindex_rag.config import load_config
from obsidian_llamaindex_rag.discover import discover_markdown_files, should_index_relative_path

from .test_config import write_config


def test_discovers_markdown_and_applies_excludes(tmp_path):
    rag_dir = tmp_path / ".vault-llamaindex-rag"
    rag_dir.mkdir()
    write_config(rag_dir / "config.yaml")
    (tmp_path / "Ideas").mkdir()
    (tmp_path / "Ideas" / "note.md").write_text("# Note\n", encoding="utf-8")
    (tmp_path / "Ideas" / "not-markdown.txt").write_text("Nope\n", encoding="utf-8")
    (tmp_path / ".obsidian").mkdir()
    (tmp_path / ".obsidian" / "workspace.md").write_text("# Ignored\n", encoding="utf-8")
    (tmp_path / "Files" / "Images").mkdir(parents=True)
    (tmp_path / "Files" / "Images" / "caption.md").write_text("# Ignored\n", encoding="utf-8")
    (rag_dir / "README.md").write_text("# Ignored\n", encoding="utf-8")

    config = load_config(rag_dir / "config.yaml")
    records = discover_markdown_files(config)

    assert [record.relative_path for record in records] == ["Ideas/note.md"]


def test_should_index_relative_path_uses_stable_posix_paths(tmp_path):
    rag_dir = tmp_path / ".vault-llamaindex-rag"
    rag_dir.mkdir()
    write_config(rag_dir / "config.yaml")
    config = load_config(rag_dir / "config.yaml")

    assert should_index_relative_path("Ideas/Research/paper.md", config)
    assert not should_index_relative_path(".vault-llamaindex-rag/README.md", config)
    assert not should_index_relative_path("Files/Images/caption.md", config)
    assert not should_index_relative_path("Ideas/Research/paper.pdf", config)

