#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from obsidian_graphrag.graphrag_cli import (
    default_paths,
    dry_run_payload,
    emit_result,
    handle_cli_error,
    index_command,
    load_graphrag_env,
    require_api_key,
    require_paid_flag,
    run_graph_rag,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Microsoft GraphRAG indexing for the vault.")
    parser.add_argument(
        "--method",
        choices=("standard", "fast", "standard-update", "fast-update"),
        default="fast",
        help="GraphRAG indexing method.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the command without running GraphRAG.")
    parser.add_argument("--allow-paid-run", action="store_true", help="Allow a paid GraphRAG indexing run.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    parser.add_argument("--verbose", action="store_true", help="Enable GraphRAG verbose logging.")
    args = parser.parse_args()

    try:
        paths = default_paths()
        cmd = index_command(paths.workspace_dir, args.method, args.dry_run, args.verbose)
        if args.dry_run:
            emit_result(dry_run_payload("index", cmd, paths), args.json)
            return 0

        require_paid_flag(args.allow_paid_run, "Indexing")
        env_values = load_graphrag_env(paths.env_path)
        require_api_key(env_values)
        if not paths.input_path.exists():
            raise FileNotFoundError(
                f"Prepared input is missing: {paths.input_path}. Run prepare_graphrag_input.py first."
            )
        return run_graph_rag(cmd, env_values)
    except Exception as exc:
        return handle_cli_error(exc)


if __name__ == "__main__":
    raise SystemExit(main())
