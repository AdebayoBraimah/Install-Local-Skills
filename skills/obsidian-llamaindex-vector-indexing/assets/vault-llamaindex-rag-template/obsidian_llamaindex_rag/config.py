from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .constants import (
    COLLECTION_NAME,
    DEFAULT_EXCLUDE_GLOBS,
    DEFAULT_INCLUDE_GLOBS,
    MANIFEST_NAME,
    RAG_DIR_NAME,
)


class ConfigError(ValueError):
    """Raised when a RAG config is invalid or unsafe."""


@dataclass(frozen=True)
class RAGConfig:
    config_path: Path
    base_dir: Path
    vault_path: Path
    rag_dir: Path
    chroma_path: Path
    manifest_path: Path
    cache_path: Path
    validation_path: Path
    log_path: Path
    collection_name: str
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    top_k_default: int
    allow_rebuild_delete: bool
    include_globs: list[str]
    exclude_globs: list[str]


def default_config_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config.yaml"


def load_config(path: str | Path | None = None) -> RAGConfig:
    config_path = Path(path).expanduser() if path else default_config_path()
    config_path = config_path.resolve()
    base_dir = config_path.parent

    raw: dict[str, Any] = {}
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
            if not isinstance(loaded, dict):
                raise ConfigError(f"Config must be a YAML mapping: {config_path}")
            raw = loaded

    def path_value(key: str, default: str) -> Path:
        value = raw.get(key, default)
        if not isinstance(value, str):
            raise ConfigError(f"{key} must be a string path")
        return (base_dir / Path(value).expanduser()).resolve()

    def int_value(key: str, default: int) -> int:
        value = raw.get(key, default)
        if not isinstance(value, int) or value <= 0:
            raise ConfigError(f"{key} must be a positive integer")
        return value

    rag_dir = path_value("rag_dir", ".")
    config = RAGConfig(
        config_path=config_path,
        base_dir=base_dir,
        vault_path=path_value("vault_path", ".."),
        rag_dir=rag_dir,
        chroma_path=path_value("chroma_path", "chroma_db"),
        manifest_path=path_value("manifest_path", MANIFEST_NAME),
        cache_path=path_value("cache_path", "cache"),
        validation_path=path_value("validation_path", "cache/validation"),
        log_path=path_value("log_path", "logs/llama_index.log"),
        collection_name=str(raw.get("collection_name", COLLECTION_NAME)),
        embedding_model=str(raw.get("embedding_model", "BAAI/bge-small-en-v1.5")),
        chunk_size=int_value("chunk_size", 800),
        chunk_overlap=int_value("chunk_overlap", 120),
        top_k_default=int_value("top_k_default", 5),
        allow_rebuild_delete=bool(raw.get("allow_rebuild_delete", False)),
        include_globs=_list_value(raw.get("include_globs"), DEFAULT_INCLUDE_GLOBS, "include_globs"),
        exclude_globs=_list_value(raw.get("exclude_globs"), DEFAULT_EXCLUDE_GLOBS, "exclude_globs"),
    )

    validate_config(config)
    return config


def _list_value(value: Any, default: list[str], key: str) -> list[str]:
    if value is None:
        return list(default)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{key} must be a list of strings")
    return list(value)


def validate_config(config: RAGConfig) -> None:
    if config.chunk_overlap >= config.chunk_size:
        raise ConfigError("chunk_overlap must be smaller than chunk_size")
    if config.collection_name.strip() == "":
        raise ConfigError("collection_name must be non-empty")
    if config.rag_dir.name != RAG_DIR_NAME:
        raise ConfigError(f"rag_dir must resolve to a directory named {RAG_DIR_NAME}")
    for key, path in {
        "chroma_path": config.chroma_path,
        "manifest_path": config.manifest_path,
        "cache_path": config.cache_path,
        "validation_path": config.validation_path,
        "log_path": config.log_path,
    }.items():
        ensure_contained(path, config.rag_dir, key)


def ensure_contained(path: Path, root: Path, label: str = "path") -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ConfigError(f"{label} resolves outside {root}") from exc

