#!/usr/bin/env bash
# Linux only; run in a fresh project directory with the application stopped.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
cd "$PROJECT_DIR"
if [[ "$(uname -s)" != Linux ]]; then echo 'Only Linux has been verified.' >&2; exit 1; fi
if [[ -x .tools/node/bin/node ]]; then export PATH="$PROJECT_DIR/.tools/node/bin:$PATH"; fi
python_bin=python3.12
if ! command -v "$python_bin" >/dev/null; then python_bin=python3; fi
python_bin="$("$python_bin" -c 'import os, sys; print(os.path.realpath(sys.executable))')"
"$python_bin" - <<'PY'
import socket,sys
if sys.version_info[:2]!=(3,12):raise SystemExit('Use the tested Python 3.12 environment.')
for port in (8000,5173):
 with socket.socket() as probe:
  if probe.connect_ex(('127.0.0.1',port))==0:raise SystemExit('Stop existing services before installing dependencies.')
PY
node -e 'if (Number(process.versions.node.split(".")[0]) !== 24) throw Error("Use the tested Node 24 environment.")'
if [[ ! -x .venv/bin/python ]]; then "$python_bin" -m venv .venv; fi
.venv/bin/python -m pip install 'torch==2.14.0+cpu' --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -r requirements-local.txt
.venv/bin/python -m pip check
npm --prefix frontend ci
npm --prefix frontend run build
printf '%s\n' 'Setup complete. Optional: copy .env.example to .env without overwriting an existing file.' 'Start: bash scripts/start_local.sh'
