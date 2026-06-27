#!/usr/bin/env bash
set -euo pipefail

RAG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_ROOT="$(cd "$RAG_DIR/.." && pwd)"
export RAG_DIR VAULT_ROOT

exec conda run -n obsidian-rag python "$RAG_DIR/search_llama_index.py" "$@"

