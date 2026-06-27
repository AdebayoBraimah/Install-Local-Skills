from __future__ import annotations

import argparse
import sys

from obsidian_llamaindex_rag.config import ConfigError, load_config
from obsidian_llamaindex_rag.logging_utils import configure_logging
from obsidian_llamaindex_rag.search import format_results, search


def main() -> int:
    parser = argparse.ArgumentParser(description="Search the Obsidian LlamaIndex vector index.")
    parser.add_argument("query", help="Search query.")
    parser.add_argument("--top-k", type=int, help="Number of results to return.")
    parser.add_argument("--config", help="Path to config.yaml.")
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        configure_logging(config.log_path)
        results = search(args.query, config, top_k=args.top_k)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2
    print(format_results(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

