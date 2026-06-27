from __future__ import annotations

import pytest
import yaml

from obsidian_llamaindex_rag.config import ConfigError, load_config


def write_config(path, **overrides):
    data = {
        "vault_path": "..",
        "rag_dir": ".",
        "chroma_path": "chroma_db",
        "manifest_path": "llama_index_manifest.json",
        "cache_path": "cache",
        "validation_path": "cache/validation",
        "log_path": "logs/llama_index.log",
        "chunk_size": 800,
        "chunk_overlap": 120,
    }
    data.update(overrides)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def test_relative_paths_resolve_from_config_dir(tmp_path):
    rag_dir = tmp_path / ".vault-llamaindex-rag"
    rag_dir.mkdir()
    config_path = rag_dir / "config.yaml"
    write_config(config_path)

    config = load_config(config_path)

    assert config.vault_path == tmp_path.resolve()
    assert config.chroma_path == (rag_dir / "chroma_db").resolve()
    assert config.manifest_path == (rag_dir / "llama_index_manifest.json").resolve()


def test_rejects_artifact_paths_outside_rag_dir(tmp_path):
    rag_dir = tmp_path / ".vault-llamaindex-rag"
    rag_dir.mkdir()
    config_path = rag_dir / "config.yaml"
    write_config(config_path, chroma_path="../outside_chroma")

    with pytest.raises(ConfigError, match="chroma_path resolves outside"):
        load_config(config_path)


def test_rejects_bad_chunk_overlap(tmp_path):
    rag_dir = tmp_path / ".vault-llamaindex-rag"
    rag_dir.mkdir()
    config_path = rag_dir / "config.yaml"
    write_config(config_path, chunk_size=100, chunk_overlap=100)

    with pytest.raises(ConfigError, match="chunk_overlap"):
        load_config(config_path)

