#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
PYTHON="$PROJECT_DIR/.venv/bin/python"
PID_FILE="$PROJECT_DIR/storage/run/app.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "App is not running (no PID file)."
  exit 0
fi

read -r app_pid < "$PID_FILE" || true
if [[ ! "$app_pid" =~ ^[0-9]+$ ]]; then
  echo "Invalid PID file: $PID_FILE" >&2
  exit 1
fi

if ! kill -0 "$app_pid" 2>/dev/null; then
  rm -f -- "$PID_FILE"
  echo "Removed stale PID file; app is not running."
  exit 0
fi

if [[ ! -r "/proc/$app_pid/cmdline" ]] ||
   [[ "$(readlink -f -- "/proc/$app_pid/cwd" 2>/dev/null || true)" != "$PROJECT_DIR" ]]; then
  echo "PID $app_pid does not match this project; refusing to stop it." >&2
  exit 1
fi

mapfile -d '' -t command_args < "/proc/$app_pid/cmdline"
if [[ "${command_args[0]:-}" != "$PYTHON" || "${command_args[1]:-}" != 'app.py' ]]; then
  echo "PID $app_pid is not this project's app.py; refusing to stop it." >&2
  exit 1
fi

kill -TERM "$app_pid"
for ((attempt = 0; attempt < 40; attempt++)); do
  if ! kill -0 "$app_pid" 2>/dev/null; then
    rm -f -- "$PID_FILE"
    echo "App stopped (PID $app_pid)."
    exit 0
  fi
  sleep 0.5
done

echo "App PID $app_pid did not exit within 20 seconds; inspect it before retrying." >&2
exit 1
