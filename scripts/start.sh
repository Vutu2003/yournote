#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
PYTHON="$PROJECT_DIR/.venv/bin/python"
RUN_DIR="$PROJECT_DIR/storage/run"
PID_FILE="$RUN_DIR/app.pid"
LOG_FILE="$RUN_DIR/app.log"

if [[ ! -x "$PYTHON" ]]; then
  echo "Missing project Python: $PYTHON" >&2
  echo "Set up the project .venv before starting the app." >&2
  exit 1
fi

mkdir -p "$RUN_DIR"
if [[ -f "$PID_FILE" ]]; then
  read -r existing_pid < "$PID_FILE" || true
  if [[ "$existing_pid" =~ ^[0-9]+$ ]] && kill -0 "$existing_pid" 2>/dev/null; then
    echo "A process is already recorded in $PID_FILE (PID $existing_pid)." >&2
    echo "Use scripts/stop.sh or inspect the PID before starting another app." >&2
    exit 1
  fi
  rm -f -- "$PID_FILE"
fi

export GRADIO_SERVER_NAME="${GRADIO_SERVER_NAME:-127.0.0.1}"
export GRADIO_SERVER_PORT="${GRADIO_SERVER_PORT:-7860}"

if ! "$PYTHON" - "$GRADIO_SERVER_NAME" "$GRADIO_SERVER_PORT" <<'PY'
import socket
import sys

host, port = sys.argv[1], int(sys.argv[2])
probe_host = "127.0.0.1" if host == "0.0.0.0" else host
try:
    with socket.create_connection((probe_host, port), timeout=1):
        pass
except OSError:
    sys.exit(0)
sys.exit(1)
PY
then
  echo "A service already responds on $GRADIO_SERVER_NAME:$GRADIO_SERVER_PORT." >&2
  exit 1
fi

cd "$PROJECT_DIR"
: > "$LOG_FILE"
PYTHONUNBUFFERED=1 nohup setsid "$PYTHON" app.py > "$LOG_FILE" 2>&1 < /dev/null &
app_pid=$!
printf '%s\n' "$app_pid" > "$PID_FILE"

for ((attempt = 0; attempt < 60; attempt++)); do
  if ! kill -0 "$app_pid" 2>/dev/null; then
    rm -f -- "$PID_FILE"
    echo "App exited during startup. Recent log output:" >&2
    tail -n 20 "$LOG_FILE" >&2
    exit 1
  fi
  if grep -q 'Running on local URL:' "$LOG_FILE"; then
    local_url="$(sed -n 's/.*Running on local URL:[[:space:]]*//p' "$LOG_FILE" | tail -n 1)"
    echo "App started (PID $app_pid): $local_url"
    echo "Log: $LOG_FILE"
    exit 0
  fi
  sleep 1
done

kill -TERM "$app_pid" 2>/dev/null || true
rm -f -- "$PID_FILE"
echo "App did not report a local URL within 60 seconds. Recent log output:" >&2
tail -n 20 "$LOG_FILE" >&2
exit 1
