#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
cd "$PROJECT_DIR"
exec "$PROJECT_DIR/.venv/bin/python" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
