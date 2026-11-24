#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="/app/src:/app"
/opt/venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
node node_modules/next/dist/bin/next start -H 0.0.0.0 -p "${PORT:-3000}" &
FRONTEND_PID=$!

cleanup() {
    kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}

trap cleanup EXIT
trap 'exit 143' TERM
trap 'exit 130' INT
wait -n "$BACKEND_PID" "$FRONTEND_PID"
