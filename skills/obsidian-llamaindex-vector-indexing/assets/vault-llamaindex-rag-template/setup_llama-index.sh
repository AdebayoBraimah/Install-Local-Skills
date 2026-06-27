#!/usr/bin/env bash
set -euo pipefail

RAG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_ROOT="$(cd "$RAG_DIR/.." && pwd)"
export RAG_DIR VAULT_ROOT

exec python3 "$RAG_DIR/setup_llama_index_conda.py" "$@"

