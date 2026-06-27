from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


GRAPHRAG_DIR_NAME = ".vault-graphrag"
WORKSPACE_DIR_NAME = "workspace"
ENV_FILE_NAME = ".env"
DEFAULT_MODEL = "gpt-5-nano"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
ALLOWED_ENV_KEYS = ("GRAPHRAG_API_KEY", "GRAPHRAG_MODEL", "GRAPHRAG_EMBEDDING_MODEL")


class GraphRAGCliError(RuntimeError):
    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass(frozen=True)
class GraphRAGPaths:
    vault_root: Path
    graphrag_dir: Path
    workspace_dir: Path
    env_path: Path
    input_path: Path


def default_paths() -> GraphRAGPaths:
    graphrag_dir = Path(__file__).resolve().parents[1]
    vault_root = graphrag_dir.parent
    workspace_dir = graphrag_dir / WORKSPACE_DIR_NAME
    return GraphRAGPaths(
        vault_root=vault_root,
        graphrag_dir=graphrag_dir,
        workspace_dir=workspace_dir,
        env_path=workspace_dir / ENV_FILE_NAME,
        input_path=workspace_dir / "input" / "obsidian_graphrag_input.json",
    )


def require_paid_flag(allowed: bool, operation: str) -> None:
    if not allowed:
        raise GraphRAGCliError(
            f"{operation} is a paid GraphRAG operation. Re-run with the explicit allow flag.",
            exit_code=2,
        )


def load_graphrag_env(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {
        "GRAPHRAG_MODEL": DEFAULT_MODEL,
        "GRAPHRAG_EMBEDDING_MODEL": DEFAULT_EMBEDDING_MODEL,
    }
    if env_path.exists():
        values.update(_load_dotenv_values(env_path))
    for key in ALLOWED_ENV_KEYS:
        if key in os.environ and os.environ[key]:
            values[key] = os.environ[key]
    return {key: value for key, value in values.items() if key in ALLOWED_ENV_KEYS and value}


def has_real_api_key(values: dict[str, str]) -> bool:
    key = values.get("GRAPHRAG_API_KEY", "").strip()
    if not key:
        return False
    lowered = key.lower()
    return not (
        lowered in {"changeme", "replace-me", "not-set", "not-used", "dummy"}
        or lowered.startswith("replace")
        or lowered.startswith("your-")
        or lowered.startswith("<")
    )


def require_api_key(values: dict[str, str]) -> None:
    if not has_real_api_key(values):
        raise GraphRAGCliError(
            "Missing real GRAPHRAG_API_KEY in .vault-graphrag/workspace/.env.",
            exit_code=2,
        )


def build_child_env(values: dict[str, str]) -> dict[str, str]:
    safe_keys = {
        "PATH",
        "HOME",
        "LANG",
        "LC_ALL",
        "SSL_CERT_FILE",
        "REQUESTS_CA_BUNDLE",
        "CONDA_PREFIX",
        "CONDA_DEFAULT_ENV",
        "PYTHONPATH",
    }
    child = {key: value for key, value in os.environ.items() if key in safe_keys and value}
    child.update({key: values[key] for key in ALLOWED_ENV_KEYS if key in values})
    return child


def graphrag_executable() -> str:
    executable = shutil.which("graphrag")
    if executable:
        return executable
    return "graphrag"


def index_command(root: Path, method: str, dry_run: bool, verbose: bool) -> list[str]:
    cmd = [graphrag_executable(), "index", "--root", str(root), "--method", method]
    if dry_run:
        cmd.append("--dry-run")
    if verbose:
        cmd.append("--verbose")
    return cmd


def query_command(
    root: Path,
    query: str,
    method: str,
    data: Path | None,
    response_type: str | None,
    dry_run: bool,
    verbose: bool,
) -> list[str]:
    cmd = [graphrag_executable(), "query", "--root", str(root), "--method", method]
    if data is not None:
        cmd.extend(["--data", str(data)])
    if response_type:
        cmd.extend(["--response-type", response_type])
    if verbose:
        cmd.append("--verbose")
    cmd.append(query)
    if dry_run:
        return cmd
    return cmd


def run_graph_rag(cmd: list[str], env_values: dict[str, str]) -> int:
    completed = subprocess.run(cmd, env=build_child_env(env_values), check=False)
    return completed.returncode


def dry_run_payload(operation: str, cmd: list[str], paths: GraphRAGPaths) -> dict[str, Any]:
    return {
        "operation": operation,
        "dry_run": True,
        "workspace": str(paths.workspace_dir),
        "input": str(paths.input_path),
        "command": cmd,
    }


def emit_result(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    for key, value in payload.items():
        if isinstance(value, list):
            print(f"{key}: {' '.join(value)}")
        else:
            print(f"{key}: {value}")


def handle_cli_error(exc: Exception) -> int:
    if isinstance(exc, GraphRAGCliError):
        print(str(exc), file=sys.stderr)
        return exc.exit_code
    print(f"GraphRAG wrapper failed: {exc}", file=sys.stderr)
    return 1


def _parse_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key not in ALLOWED_ENV_KEYS:
            continue
        values[key] = _clean_env_value(value)
    return values


def _load_dotenv_values(path: Path) -> dict[str, str]:
    try:
        from dotenv import dotenv_values
    except ImportError:
        return _parse_dotenv(path)
    loaded = dotenv_values(path)
    return {
        key: str(value)
        for key, value in loaded.items()
        if key in ALLOWED_ENV_KEYS and value is not None and str(value)
    }


def _clean_env_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value
