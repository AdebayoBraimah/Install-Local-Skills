from __future__ import annotations

import argparse
import os
import sys

from obsidian_llamaindex_rag.config import ConfigError, load_config
from obsidian_llamaindex_rag.index import validate_smoke_index
from obsidian_llamaindex_rag.logging_utils import configure_logging


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate LlamaIndex, HuggingFace embeddings, and Chroma.")
    parser.add_argument("--config", help="Path to config.yaml.")
    args = parser.parse_args()

    os.environ.setdefault("OPENAI_API_KEY", "not-used-by-obsidian-llamaindex-rag")
    try:
        config = load_config(args.config)
        configure_logging(config.log_path)
        result = validate_smoke_index(config)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1

    summary = result["summary"]
    results = result["results"]
    if not results:
        print("Validation failed: smoke search returned no results.", file=sys.stderr)
        return 1
    print(
        "Validation complete: "
        f"indexed={summary.indexed} chunks={summary.chunks_added} "
        f"validation_root={result['validation_root']}"
    )
    print(f"Top validation result: {results[0].source_path} score={results[0].score}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

