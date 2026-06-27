from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


GRAPHRAG_DIR_NAME = ".vault-graphrag"


class ConfigError(ValueError):
    """Raised when GraphRAG vault configuration is invalid."""


@dataclass(frozen=True)
class GraphRAGConfig:
    config_path: Path
    base_dir: Path
    vault_path: Path
    graphrag_dir: Path
    workspace_path: Path
    input_json_path: Path
    manifest_path: Path
    ignore_patterns_path: Path
    include_globs: list[str]
    referenced_image_dirs: list[Path]
    image_context_lines: int
    image_context_chars: int


def default_config_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config" / "graphrag_config.yaml"


def load_config(path: str | Path | None = None) -> GraphRAGConfig:
    config_path = Path(path).expanduser() if path else default_config_path()
    config_path = config_path.resolve()
    base_dir = config_path.parent.parent
    raw = _load_yaml_mapping(config_path)

    def path_value(key: str, default: str) -> Path:
        value = raw.get(key, default)
        if not isinstance(value, str):
            raise ConfigError(f"{key} must be a string path")
        return (base_dir / Path(value).expanduser()).resolve()

    graphrag_dir = path_value("graphrag_dir", ".")
    vault_path = path_value("vault_path", "..")
    referenced_dirs = [
        (vault_path / Path(item)).resolve()
        for item in _string_list(raw.get("referenced_image_dirs"), ["Files/Images"], "referenced_image_dirs")
    ]
    config = GraphRAGConfig(
        config_path=config_path,
        base_dir=base_dir,
        vault_path=vault_path,
        graphrag_dir=graphrag_dir,
        workspace_path=path_value("workspace_path", "workspace"),
        input_json_path=path_value("input_json_path", "workspace/input/obsidian_graphrag_input.json"),
        manifest_path=path_value("manifest_path", "manifests/graphrag_input_manifest.json"),
        ignore_patterns_path=path_value("ignore_patterns_path", "config/ignore_patterns.txt"),
        include_globs=_string_list(raw.get("include_globs"), ["**/*.md"], "include_globs"),
        referenced_image_dirs=referenced_dirs,
        image_context_lines=_positive_int(raw.get("image_context_lines", 3), "image_context_lines"),
        image_context_chars=_positive_int(raw.get("image_context_chars", 1000), "image_context_chars"),
    )
    validate_config(config)
    return config


def validate_config(config: GraphRAGConfig) -> None:
    if config.graphrag_dir.name != GRAPHRAG_DIR_NAME:
        raise ConfigError(f"graphrag_dir must resolve to a directory named {GRAPHRAG_DIR_NAME}")
    if not config.vault_path.exists():
        raise ConfigError(f"vault_path does not exist: {config.vault_path}")
    for key, path in {
        "workspace_path": config.workspace_path,
        "input_json_path": config.input_json_path,
        "manifest_path": config.manifest_path,
        "ignore_patterns_path": config.ignore_patterns_path,
    }.items():
        _ensure_contained(path, config.graphrag_dir, key)
    if not config.ignore_patterns_path.exists():
        raise ConfigError(f"ignore patterns file does not exist: {config.ignore_patterns_path}")


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"config file does not exist: {path}")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ConfigError(f"config file must contain a YAML mapping: {path}")
    return loaded


def _string_list(value: Any, default: list[str], key: str) -> list[str]:
    if value is None:
        return list(default)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{key} must be a list of strings")
    return list(value)


def _positive_int(value: Any, key: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise ConfigError(f"{key} must be a positive integer")
    return value


def _ensure_contained(path: Path, root: Path, label: str) -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ConfigError(f"{label} resolves outside {root}") from exc
