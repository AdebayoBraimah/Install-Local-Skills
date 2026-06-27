#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import stat
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install the vault-local .vault-graphrag scaffold into an Obsidian vault or Markdown repo."
    )
    parser.add_argument(
        "vault_root",
        nargs="?",
        default=".",
        help="Target vault/repo root. Defaults to the current directory.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing .vault-graphrag directory. Use carefully.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be copied without writing files.",
    )
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parents[1]
    template_dir = skill_dir / "templates" / "vault-graphrag"
    vault_root = Path(args.vault_root).expanduser().resolve()
    target_dir = vault_root / ".vault-graphrag"

    if not template_dir.exists():
        print(f"Template directory is missing: {template_dir}", file=sys.stderr)
        return 1
    if not vault_root.exists() or not vault_root.is_dir():
        print(f"Target vault root does not exist or is not a directory: {vault_root}", file=sys.stderr)
        return 2
    if target_dir.exists() and not args.overwrite:
        print(
            f"{target_dir} already exists. Re-run with --overwrite only if you intend to replace it.",
            file=sys.stderr,
        )
        return 2

    if args.dry_run:
        action = "overwrite" if target_dir.exists() else "create"
        print(f"Would {action}: {target_dir}")
        print(f"Template: {template_dir}")
        return 0

    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(template_dir, target_dir)
    make_scripts_executable(target_dir)
    print(f"Installed GraphRAG scaffold: {target_dir}")
    print("Next: cd to the vault root and run bash .vault-graphrag/scripts/setup_graphrag.sh")
    return 0


def make_scripts_executable(graphrag_dir: Path) -> None:
    scripts_dir = graphrag_dir / "scripts"
    if not scripts_dir.exists():
        return
    for path in scripts_dir.iterdir():
        if path.suffix not in {".sh", ".py"}:
            continue
        mode = path.stat().st_mode
        path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


if __name__ == "__main__":
    raise SystemExit(main())
