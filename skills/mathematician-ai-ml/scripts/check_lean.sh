#!/usr/bin/env bash
set -euo pipefail

if ! command -v lean >/dev/null 2>&1; then
  echo "Missing required command: lean" >&2
  echo "Install Lean 4 before attempting Lean verification." >&2
  exit 1
fi

if ! command -v lake >/dev/null 2>&1; then
  echo "Missing required command: lake" >&2
  echo "Install Lake before attempting Lean project verification." >&2
  exit 1
fi

echo "lean:"
lean --version

echo "lake:"
lake --version
