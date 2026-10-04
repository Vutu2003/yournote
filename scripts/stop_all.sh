#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
if [[ ! -x "$PROJECT_DIR/.venv/bin/python" ]]; then
  echo "Missing project Python: $PROJECT_DIR/.venv/bin/python" >&2
  exit 1
fi
exec "$PROJECT_DIR/.venv/bin/python" "$SCRIPT_DIR/runtime.py" stop
