#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE_DIR="$SKILL_DIR/assets/vault-llamaindex-rag-template"
TARGET_ROOT="${1:-$PWD}"
TARGET_ROOT="$(cd "$TARGET_ROOT" && pwd)"
TARGET_RAG_DIR="$TARGET_ROOT/.vault-llamaindex-rag"

if [[ -e "$TARGET_RAG_DIR" ]]; then
  echo "Scaffold already exists: $TARGET_RAG_DIR"
  exit 0
fi

if [[ ! -d "$TEMPLATE_DIR" ]]; then
  echo "Missing scaffold template: $TEMPLATE_DIR" >&2
  exit 1
fi

mkdir -p "$TARGET_RAG_DIR"

if command -v rsync >/dev/null 2>&1; then
  rsync -a "$TEMPLATE_DIR"/ "$TARGET_RAG_DIR"/
else
  cp -R "$TEMPLATE_DIR"/. "$TARGET_RAG_DIR"/
fi

chmod +x "$TARGET_RAG_DIR"/*_llama-index.sh

echo "Created scaffold: $TARGET_RAG_DIR"

