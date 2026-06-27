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
    load_graphrag_env,
    query_command,
    require_api_key,
    require_paid_flag,
    run_graph_rag,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Query the Microsoft GraphRAG vault index.")
    parser.add_argument("query", help="Question or synthesis prompt.")
    parser.add_argument(
        "--method",
        choices=("local", "global", "drift", "basic"),
        default="global",
        help="GraphRAG query method.",
    )
    parser.add_argument("--data", help="Optional GraphRAG output directory containing parquet files.")
    parser.add_argument("--response-type", help="Optional response format hint for GraphRAG.")
    parser.add_argument("--dry-run", action="store_true", help="Print the command without running GraphRAG.")
    parser.add_argument("--allow-paid-query", action="store_true", help="Allow a paid GraphRAG query.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    parser.add_argument("--verbose", action="store_true", help="Enable GraphRAG verbose logging.")
    args = parser.parse_args()

    try:
        paths = default_paths()
        data = paths.workspace_dir / args.data if args.data else None
        cmd = query_command(
            paths.workspace_dir,
            args.query,
            args.method,
            data,
            args.response_type,
            args.dry_run,
            args.verbose,
        )
        if args.dry_run:
            emit_result(dry_run_payload("query", cmd, paths), args.json)
            return 0

        require_paid_flag(args.allow_paid_query, "Querying")
        env_values = load_graphrag_env(paths.env_path)
        require_api_key(env_values)
        return run_graph_rag(cmd, env_values)
    except Exception as exc:
        return handle_cli_error(exc)


if __name__ == "__main__":
    raise SystemExit(main())
