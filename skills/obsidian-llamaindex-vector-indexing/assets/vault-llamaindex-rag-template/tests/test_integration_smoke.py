from __future__ import annotations

import importlib.util

import pytest

from obsidian_llamaindex_rag.config import load_config
from obsidian_llamaindex_rag.index import validate_smoke_index

from .test_config import write_config


@pytest.mark.integration
def test_validation_smoke_index_without_openai_key(tmp_path, monkeypatch):
    required = [
        "chromadb",
        "llama_index.core",
        "llama_index.embeddings.huggingface",
        "llama_index.vector_stores.chroma",
    ]
    missing = [name for name in required if importlib.util.find_spec(name) is None]
    if missing:
        pytest.skip(f"missing integration dependencies: {missing}")

    rag_dir = tmp_path / ".vault-llamaindex-rag"
    rag_dir.mkdir()
    write_config(rag_dir / "config.yaml", validation_path="cache/validation")
    config = load_config(rag_dir / "config.yaml")
    monkeypatch.setenv("OPENAI_API_KEY", "poisoned-unused-key")

    result = validate_smoke_index(config)

    assert result["summary"].indexed == 1
    assert result["results"]
    assert result["results"][0].source_path == "sample.md"

