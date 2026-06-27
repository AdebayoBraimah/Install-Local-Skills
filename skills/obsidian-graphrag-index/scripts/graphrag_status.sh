#!/usr/bin/env bash
set -euo pipefail

ROOT="${VAULT_ROOT:-$(pwd)}"
cd "$ROOT"

if [[ ! -f .vault-graphrag/config/active_env.json ]]; then
  echo "GraphRAG environment is not configured. Run: bash .vault-graphrag/scripts/setup_graphrag.sh"
  exit 2
fi

bash .vault-graphrag/scripts/run_in_env.sh python .vault-graphrag/scripts/validate_graphrag.py --json
