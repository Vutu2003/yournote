#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
exec "${YOURNOTE_PYTHON:-$PROJECT_DIR/.venv/bin/python}" "$SCRIPT_DIR/runtime.py" start-local
