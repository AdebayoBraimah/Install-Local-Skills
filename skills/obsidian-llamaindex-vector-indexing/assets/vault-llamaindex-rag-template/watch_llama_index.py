from __future__ import annotations

import argparse
import sys

from obsidian_llamaindex_rag.config import ConfigError, load_config
from obsidian_llamaindex_rag.logging_utils import configure_logging
from obsidian_llamaindex_rag.watch import watch_vault


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch the vault and incrementally update the LlamaIndex index.")
    parser.add_argument("--config", help="Path to config.yaml.")
    parser.add_argument("--debounce", type=float, default=2.0, help="Debounce window in seconds.")
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        configure_logging(config.log_path)
        watch_vault(config, debounce=args.debounce)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

