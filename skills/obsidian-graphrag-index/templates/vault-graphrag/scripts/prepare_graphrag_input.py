#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from obsidian_graphrag.config import ConfigError, load_config
from obsidian_graphrag.staging import prepare_input


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare Obsidian Markdown as GraphRAG JSON input.")
    parser.add_argument("--config", help="Path to graphrag_config.yaml.")
    parser.add_argument("--dry-run", action="store_true", help="Preview the corpus without writing output files.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        result = prepare_input(config, dry_run=args.dry_run)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Prepare failed: {exc}", file=sys.stderr)
        return 1

    payload = asdict(result)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            f"Prepared {result.document_count} documents "
            f"dry_run={result.dry_run} output={result.output_path}"
        )
        if result.warnings:
            print(f"Warnings: {len(result.warnings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
