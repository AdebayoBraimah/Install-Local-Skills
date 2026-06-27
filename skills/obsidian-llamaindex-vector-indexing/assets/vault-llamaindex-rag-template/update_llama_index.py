from __future__ import annotations

import argparse
import sys

from obsidian_llamaindex_rag.config import ConfigError, load_config
from obsidian_llamaindex_rag.index import update_index
from obsidian_llamaindex_rag.logging_utils import configure_logging


def main() -> int:
    parser = argparse.ArgumentParser(description="Incrementally update the Obsidian LlamaIndex Chroma index.")
    parser.add_argument("--dry-run", action="store_true", help="Detect changes without mutating Chroma or manifest.")
    parser.add_argument("--config", help="Path to config.yaml.")
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        configure_logging(config.log_path)
        summary = update_index(config, dry_run=args.dry_run)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2
    prefix = "Dry run" if summary.dry_run else "Update complete"
    print(
        f"{prefix}: discovered={summary.discovered} indexed={summary.indexed} "
        f"deleted={summary.deleted} unchanged={summary.unchanged} chunks={summary.chunks_added}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

