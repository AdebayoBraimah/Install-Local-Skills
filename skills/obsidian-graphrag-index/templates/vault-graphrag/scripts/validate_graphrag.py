#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from obsidian_graphrag.config import ConfigError, load_config
from obsidian_graphrag.graphrag_cli import has_real_api_key, load_graphrag_env


SECRET_KEY_RE = re.compile(r"sk-[A-Za-z0-9_-]{16,}")
API_KEY_ASSIGN_RE = re.compile(r"^\s*GRAPHRAG_API_KEY\s*=\s*(.+?)\s*$")
REQUIRED_METADATA = {
    "source_path",
    "sha256",
    "mtime_ns",
    "tags",
    "aliases",
    "keywords",
    "category",
    "wikilinks",
    "image_refs",
    "sidecar_paths",
    "warning_count",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the vault-local Microsoft GraphRAG workflow.")
    parser.add_argument("--config", help="Path to graphrag_config.yaml.")
    parser.add_argument("--paid", action="store_true", help="Require a real local GraphRAG API key.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        payload = validate(config)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1

    secrets = payload["secrets"]
    if args.paid and not secrets["present"]:
        emit(payload, args.json)
        return 2
    if payload["errors"]:
        emit(payload, args.json)
        return 1
    emit(payload, args.json)
    return 0


def validate(config) -> dict[str, Any]:
    graphrag_dir = config.graphrag_dir
    workspace = config.workspace_path
    env_path = workspace / ".env"
    env_values = load_graphrag_env(env_path)
    secret_findings = scan_for_tracked_secrets(graphrag_dir)
    errors: list[str] = []
    warnings: list[str] = []

    if secret_findings:
        errors.extend(secret_findings)
    settings_template = graphrag_dir / "config" / "settings.template.yaml"
    if not settings_template.exists():
        errors.append(f"missing settings template: {settings_template}")
    compatibility = validate_compatibility(graphrag_dir / "config" / "graphrag_compatibility.json")
    if compatibility.get("errors"):
        errors.extend(compatibility["errors"])
    active_env_path = graphrag_dir / "config" / "active_env.json"
    if not active_env_path.exists():
        warnings.append(f"active environment manifest is missing: {active_env_path}")
    input_check = validate_input(config.input_json_path)
    errors.extend(input_check["errors"])
    warnings.extend(input_check["warnings"])

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "paths": {
            "graphrag_dir": str(graphrag_dir),
            "workspace": str(workspace),
            "input": str(config.input_json_path),
            "manifest": str(config.manifest_path),
            "active_env": str(active_env_path),
        },
        "secrets": {
            "env_file_exists": env_path.exists(),
            "present": has_real_api_key(env_values),
        },
        "compatibility": compatibility,
        "input": input_check,
    }


def validate_compatibility(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "errors": [f"missing compatibility file: {path}"]}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "errors": [f"invalid compatibility JSON: {exc}"]}
    input_contract = payload.get("input_contract", {})
    errors = []
    if input_contract.get("file_pattern") != r"^obsidian_graphrag_input\.json$":
        errors.append("compatibility input file_pattern is incorrect")
    if input_contract.get("text_column") != "text":
        errors.append("compatibility text_column is incorrect")
    if input_contract.get("title_column") != "title":
        errors.append("compatibility title_column is incorrect")
    return {"exists": True, "graphrag_version": payload.get("graphrag_version"), "errors": errors}


def validate_input(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "document_count": 0, "errors": [], "warnings": [f"input JSON is not staged: {path}"]}
    try:
        documents = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "document_count": 0, "errors": [f"invalid input JSON: {exc}"], "warnings": []}
    errors: list[str] = []
    if not isinstance(documents, list):
        errors.append("input JSON root must be an array")
        return {"exists": True, "document_count": 0, "errors": errors, "warnings": []}
    for index, document in enumerate(documents[:20]):
        if not isinstance(document, dict):
            errors.append(f"document {index} must be an object")
            continue
        for key in ("id", "title", "text", "metadata"):
            if key not in document:
                errors.append(f"document {index} missing {key}")
        metadata = document.get("metadata", {})
        if isinstance(metadata, dict):
            missing = REQUIRED_METADATA - set(metadata)
            if missing:
                errors.append(f"document {index} metadata missing {sorted(missing)}")
        else:
            errors.append(f"document {index} metadata must be an object")
        top_level_missing = REQUIRED_METADATA - set(document)
        if top_level_missing:
            errors.append(f"document {index} top-level metadata columns missing {sorted(top_level_missing)}")
    return {"exists": True, "document_count": len(documents), "errors": errors, "warnings": []}


def scan_for_tracked_secrets(root: Path) -> list[str]:
    finding_paths: set[Path] = set()
    skip_dirs = {"workspace", "logs", "manifests", ".conda", "__pycache__", ".pytest_cache"}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip_dirs for part in path.relative_to(root).parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if SECRET_KEY_RE.search(text):
            finding_paths.add(path)
        for line in text.splitlines():
            match = API_KEY_ASSIGN_RE.match(line)
            if match and _looks_like_real_key(match.group(1)):
                finding_paths.add(path)
    return [f"possible secret in tracked file: {path}" for path in sorted(finding_paths)]


def _looks_like_real_key(value: str) -> bool:
    cleaned = value.strip().strip("'\"")
    lowered = cleaned.lower()
    if not cleaned or lowered.startswith("replace") or lowered.startswith("your-"):
        return False
    if lowered in {"changeme", "dummy", "not-set", "not-used"}:
        return False
    return cleaned.startswith("sk-") or len(cleaned) > 20


def emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    if payload["ok"]:
        print("GraphRAG offline validation passed.")
    else:
        print("GraphRAG offline validation failed.")
    if payload["warnings"]:
        print(f"Warnings: {len(payload['warnings'])}")


if __name__ == "__main__":
    raise SystemExit(main())
