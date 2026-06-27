from __future__ import annotations

from obsidian_llamaindex_rag.config import load_config
from obsidian_llamaindex_rag.index import update_index
from obsidian_llamaindex_rag.manifest import empty_manifest, write_manifest_atomic

from .test_config import write_config


def test_update_dry_run_does_not_write_manifest_or_chroma(tmp_path):
    rag_dir = tmp_path / ".vault-llamaindex-rag"
    rag_dir.mkdir()
    write_config(rag_dir / "config.yaml")
    note = tmp_path / "note.md"
    note.write_text("# Note\n", encoding="utf-8")
    config = load_config(rag_dir / "config.yaml")
    write_manifest_atomic(config.manifest_path, empty_manifest(config.collection_name))
    before = config.manifest_path.read_text(encoding="utf-8")

    summary = update_index(config, dry_run=True)

    assert summary.dry_run
    assert summary.indexed == 1
    assert config.manifest_path.read_text(encoding="utf-8") == before
    assert not config.chroma_path.exists()

