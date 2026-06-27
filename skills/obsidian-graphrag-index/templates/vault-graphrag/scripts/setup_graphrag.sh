#!/usr/bin/env bash
set -euo pipefail

GRAPHRAG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VAULT_ROOT="$(cd "$GRAPHRAG_DIR/.." && pwd)"
export PYTHONPATH="$GRAPHRAG_DIR${PYTHONPATH:+:$PYTHONPATH}"

cd "$VAULT_ROOT"
exec python "$GRAPHRAG_DIR/obsidian_graphrag/env_setup.py" "$@"
