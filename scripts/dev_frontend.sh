#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
if [[ -x "$PROJECT_DIR/.tools/node/bin/node" ]]; then
  export PATH="$PROJECT_DIR/.tools/node/bin:$PATH"
fi
cd "$PROJECT_DIR/frontend"
exec npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
