#!/usr/bin/env bash
set -euo pipefail

GRAPHRAG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VAULT_ROOT="$(cd "$GRAPHRAG_DIR/.." && pwd)"
ACTIVE_ENV="$GRAPHRAG_DIR/config/active_env.json"

if [[ ! -f "$ACTIVE_ENV" ]]; then
  echo "Missing $ACTIVE_ENV. Run: bash .vault-graphrag/scripts/setup_graphrag.sh" >&2
  exit 2
fi

if [[ $# -lt 1 ]]; then
  echo "Usage: run_in_env.sh COMMAND [ARGS...]" >&2
  exit 2
fi

read -r ENV_TYPE ENV_VALUE < <(python - "$ACTIVE_ENV" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as handle:
    data = json.load(handle)
env_type = data.get("type")
if env_type == "named":
    print("named", data["name"])
elif env_type == "prefix":
    print("prefix", data["path"])
else:
    raise SystemExit(f"unknown active env type: {env_type}")
PY
)

export PYTHONPATH="$GRAPHRAG_DIR${PYTHONPATH:+:$PYTHONPATH}"
eval "$(python - "$GRAPHRAG_DIR/workspace/.env" <<'PY'
import shlex
import sys
from pathlib import Path

env_path = Path(sys.argv[1])
allowed = {
    "GRAPHRAG_API_KEY",
    "GRAPHRAG_MODEL",
    "GRAPHRAG_EMBEDDING_MODEL",
}
values = {
    "GRAPHRAG_MODEL": "gpt-5-nano",
    "GRAPHRAG_EMBEDDING_MODEL": "text-embedding-3-small",
}
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key not in allowed:
            continue
        value = value.strip().strip("'\"")
        if value:
            values[key] = value
for key, value in values.items():
    print(f"export {key}={shlex.quote(value)}")
PY
)"
cd "$VAULT_ROOT"

if [[ "$ENV_TYPE" == "named" ]]; then
  exec conda run --name "$ENV_VALUE" "$@"
fi

exec conda run --prefix "$ENV_VALUE" "$@"
