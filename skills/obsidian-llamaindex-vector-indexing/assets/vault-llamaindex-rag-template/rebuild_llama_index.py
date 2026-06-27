from __future__ import annotations

import argparse
import sys

from obsidian_llamaindex_rag.config import ConfigError, load_config
from obsidian_llamaindex_rag.index import rebuild_index
from obsidian_llamaindex_rag.logging_utils import configure_logging


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild the Obsidian LlamaIndex Chroma index.")
    parser.add_argument("--force", action="store_true", help="Allow deleting the existing Chroma DB and manifest.")
    parser.add_argument("--config", help="Path to config.yaml.")
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        configure_logging(config.log_path)
        summary = rebuild_index(config, force=args.force)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2
    print(
        f"Rebuild complete: discovered={summary.discovered} indexed={summary.indexed} "
        f"chunks={summary.chunks_added}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

