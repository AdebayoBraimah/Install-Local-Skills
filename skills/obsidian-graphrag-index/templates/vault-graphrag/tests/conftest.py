from __future__ import annotations

import sys
from pathlib import Path

import pytest

from obsidian_graphrag.config import GraphRAGConfig


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


@pytest.fixture()
def sample_config(tmp_path: Path) -> GraphRAGConfig:
    vault = tmp_path / "vault"
    graphrag = vault / ".vault-graphrag"
    (vault / "Ideas").mkdir(parents=True)
    (vault / "Files" / "Images").mkdir(parents=True)
    (graphrag / "workspace" / "input").mkdir(parents=True)
    (graphrag / "manifests").mkdir(parents=True)
    (graphrag / "config").mkdir(parents=True)
    ignore_path = graphrag / "config" / "ignore_patterns.txt"
    ignore_path.write_text(
        "\n".join(
            [
                ".vault-graphrag/",
                ".obsidian/",
                "Templates/",
                "Ideas/Meetings/",
                "meeting-*.md",
                "AGENTS.md",
            ]
        ),
        encoding="utf-8",
    )
    return GraphRAGConfig(
        config_path=graphrag / "config" / "graphrag_config.yaml",
        base_dir=graphrag,
        vault_path=vault,
        graphrag_dir=graphrag,
        workspace_path=graphrag / "workspace",
        input_json_path=graphrag / "workspace" / "input" / "obsidian_graphrag_input.json",
        manifest_path=graphrag / "manifests" / "graphrag_input_manifest.json",
        ignore_patterns_path=ignore_path,
        include_globs=["**/*.md", "*.md"],
        referenced_image_dirs=[vault / "Files" / "Images"],
        image_context_lines=3,
        image_context_chars=1000,
    )
