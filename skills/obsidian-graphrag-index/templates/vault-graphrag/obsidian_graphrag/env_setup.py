from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LLAMAINDEX_ENV = "obsidian-rag"
GRAPHRAG_ENV = "obsidian-graphrag"
DEFAULT_MODEL = "gpt-5-nano"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
SETUP_TIMEOUT_SECONDS = 20 * 60


class SetupError(RuntimeError):
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision the vault-local Microsoft GraphRAG workflow.")
    parser.add_argument("--force-env", action="store_true", help="Re-provision the GraphRAG conda environment.")
    parser.add_argument(
        "--force-settings",
        action="store_true",
        help="Overwrite workspace/settings.yaml from config/settings.template.yaml.",
    )
    parser.add_argument(
        "--refresh-compat",
        action="store_true",
        help="Refresh config/graphrag_compatibility.json even if it appears current.",
    )
    args = parser.parse_args()

    paths = setup_paths()
    paths["logs"].mkdir(parents=True, exist_ok=True)
    paths["workspace"].mkdir(parents=True, exist_ok=True)

    try:
        conda = shutil.which("conda")
        if not conda:
            raise SetupError("conda was not found on PATH")

        active = None if args.force_env else load_active_env(paths["active_env"])
        if active and is_expected_active_env(active) and validate_active_env(conda, active):
            print(f"Reusing GraphRAG environment: {describe_env(active)}")
        else:
            active = provision_environment(conda, paths)
            write_json(paths["active_env"], active)
            print(f"Wrote {paths['active_env']}")

        ensure_workspace_env(paths)
        ensure_settings(conda, active, paths, force=args.force_settings)
        ensure_compatibility(conda, active, paths, force=args.refresh_compat)
        print("GraphRAG setup complete.")
        return 0
    except SetupError as exc:
        print(f"Setup failed: {exc}", file=sys.stderr)
        return 1


def setup_paths() -> dict[str, Path]:
    graphrag_dir = Path(__file__).resolve().parents[1]
    vault_root = graphrag_dir.parent
    return {
        "vault_root": vault_root,
        "graphrag_dir": graphrag_dir,
        "workspace": graphrag_dir / "workspace",
        "logs": graphrag_dir / "logs",
        "active_env": graphrag_dir / "config" / "active_env.json",
        "compat": graphrag_dir / "config" / "graphrag_compatibility.json",
        "settings_template": graphrag_dir / "config" / "settings.template.yaml",
        "environment": graphrag_dir / "environment.yml",
        "env_example": graphrag_dir / ".env.example",
    }


def provision_environment(conda: str, paths: dict[str, Path]) -> dict[str, Any]:
    if llamaindex_validation_script(paths).exists():
        pre_validate_llamaindex(paths)
    else:
        print("Skipping LlamaIndex pre-validation; .vault-llamaindex-rag was not found.")

    if named_env_exists(conda, LLAMAINDEX_ENV):
        export_existing_environment(conda, paths)
    else:
        print(f"Skipping {LLAMAINDEX_ENV} snapshot; conda environment was not found.")

    create_or_update_named_env(conda, paths)
    active = {
        "type": "named",
        "name": GRAPHRAG_ENV,
        "created_at": now_iso(),
        "strategy": "dedicated-named-env",
    }
    verify_graphrag_env(conda, active)
    return active


def pre_validate_llamaindex(paths: dict[str, Path]) -> None:
    script = llamaindex_validation_script(paths)
    if not script.exists():
        raise SetupError(f"LlamaIndex validation script is missing: {script}")
    run(["bash", str(script)], timeout=SETUP_TIMEOUT_SECONDS)


def llamaindex_validation_script(paths: dict[str, Path]) -> Path:
    return paths["vault_root"] / ".vault-llamaindex-rag" / "validate_llama-index.sh"


def export_existing_environment(conda: str, paths: dict[str, Path]) -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_path = paths["logs"] / f"{LLAMAINDEX_ENV}_{timestamp}.environment.yml"
    list_path = paths["logs"] / f"{LLAMAINDEX_ENV}_{timestamp}.conda-list.txt"
    freeze_path = paths["logs"] / f"{LLAMAINDEX_ENV}_{timestamp}.pip-freeze.txt"
    write_command_output([conda, "env", "export", "--name", LLAMAINDEX_ENV], export_path)
    write_command_output([conda, "list", "--name", LLAMAINDEX_ENV], list_path)
    write_command_output([conda, "run", "--name", LLAMAINDEX_ENV, "python", "-m", "pip", "freeze"], freeze_path)


def create_or_update_named_env(conda: str, paths: dict[str, Path]) -> None:
    if named_env_exists(conda, GRAPHRAG_ENV):
        run(
            [
                conda,
                "env",
                "update",
                "--name",
                GRAPHRAG_ENV,
                "--file",
                str(paths["environment"]),
                "--prune",
            ],
            timeout=SETUP_TIMEOUT_SECONDS,
        )
        return
    run(
        [conda, "env", "create", "--name", GRAPHRAG_ENV, "--file", str(paths["environment"])],
        timeout=SETUP_TIMEOUT_SECONDS,
    )


def verify_graphrag_env(conda: str, active: dict[str, Any]) -> None:
    run(conda_run_cmd(conda, active, ["python", "-m", "pip", "check"]), timeout=SETUP_TIMEOUT_SECONDS)
    run(conda_run_cmd(conda, active, ["graphrag", "--help"]), timeout=120)
    run(conda_run_cmd(conda, active, ["python", "-c", "import graphrag"]), timeout=120)


def ensure_workspace_env(paths: dict[str, Path]) -> None:
    env_path = paths["workspace"] / ".env"
    if env_path.exists():
        return
    shutil.copy2(paths["env_example"], env_path)
    print(f"Created placeholder env file at {env_path}")


def ensure_settings(conda: str, active: dict[str, Any], paths: dict[str, Path], force: bool) -> None:
    settings = paths["workspace"] / "settings.yaml"
    if settings.exists() and not force:
        return
    generated_backup = paths["logs"] / f"graphrag_generated_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
    run(conda_run_cmd(conda, active, ["graphrag", "init", "--root", str(paths["workspace"]), "--model", DEFAULT_MODEL, "--embedding", DEFAULT_EMBEDDING_MODEL, "--force"]), timeout=300)
    if settings.exists():
        shutil.copy2(settings, generated_backup)
    shutil.copy2(paths["settings_template"], settings)
    print(f"Rendered settings from template: {settings}")


def ensure_compatibility(conda: str, active: dict[str, Any], paths: dict[str, Path], force: bool) -> None:
    current_version = graphrag_version(conda, active)
    existing = load_json(paths["compat"])
    if (
        not force
        and existing
        and existing.get("graphrag_version") == current_version
        and existing.get("input_contract", {}).get("file_pattern") == r"^obsidian_graphrag_input\.json$"
    ):
        return
    payload = {
        "generated_by": "vault-graphrag-setup",
        "graphrag_version": current_version,
        "checked_at": now_iso(),
        "cli": {
            "index": ["--root", "--method", "--dry-run"],
            "query": ["--root", "--method"],
        },
        "input_contract": {
            "type": "file",
            "file_type": "json",
            "file_pattern": r"^obsidian_graphrag_input\.json$",
            "text_column": "text",
            "title_column": "title",
            "metadata": [
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
            ],
        },
    }
    write_json(paths["compat"], payload)
    print(f"Refreshed compatibility file: {paths['compat']}")


def graphrag_version(conda: str, active: dict[str, Any]) -> str:
    command = conda_run_cmd(
        conda,
        active,
        ["python", "-c", "from importlib import metadata; print(metadata.version('graphrag'))"],
    )
    completed = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if completed.returncode != 0:
        raise SetupError(completed.stderr.strip() or "could not determine GraphRAG version")
    return completed.stdout.strip()


def validate_active_env(conda: str, active: dict[str, Any]) -> bool:
    try:
        verify_graphrag_env(conda, active)
    except Exception as exc:
        print(f"Active GraphRAG env is invalid: {exc}", file=sys.stderr)
        return False
    return True


def is_expected_active_env(active: dict[str, Any]) -> bool:
    return active.get("type") == "named" and active.get("name") == GRAPHRAG_ENV


def conda_run_cmd(conda: str, active: dict[str, Any], command: list[str]) -> list[str]:
    if active.get("type") == "named":
        return [conda, "run", "--name", str(active["name"]), *command]
    if active.get("type") == "prefix":
        return [conda, "run", "--prefix", str(active["path"]), *command]
    raise SetupError(f"unknown active env type: {active.get('type')}")


def named_env_exists(conda: str, name: str) -> bool:
    completed = subprocess.run(
        [conda, "env", "list", "--json"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise SetupError(completed.stderr.strip() or "could not list conda environments")
    payload = json.loads(completed.stdout)
    envs = [Path(env_path).name for env_path in payload.get("envs", [])]
    return name in envs


def run(cmd: list[str], timeout: int, env: dict[str, str] | None = None) -> None:
    print("+ " + " ".join(cmd))
    try:
        subprocess.run(cmd, check=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired as exc:
        raise SetupError(f"command timed out after {timeout}s: {' '.join(cmd)}") from exc
    except subprocess.CalledProcessError as exc:
        raise SetupError(f"command failed with exit {exc.returncode}: {' '.join(cmd)}") from exc


def write_command_output(cmd: list[str], path: Path) -> None:
    print("+ " + " ".join(cmd) + f" > {path}")
    completed = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if completed.returncode != 0:
        raise SetupError(completed.stderr.strip() or f"command failed: {' '.join(cmd)}")
    path.write_text(completed.stdout, encoding="utf-8")


def load_active_env(path: Path) -> dict[str, Any] | None:
    loaded = load_json(path)
    return loaded if isinstance(loaded, dict) else None


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def describe_env(active: dict[str, Any]) -> str:
    if active.get("type") == "named":
        return str(active.get("name"))
    return str(active.get("path"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
