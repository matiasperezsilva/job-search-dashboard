#!/usr/bin/env bash
set -e
export PYTHONPATH="/app/src:/app"
/opt/venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
trap 'kill $BACKEND_PID 2>/dev/null || true' EXIT
exec npm start -- -H 0.0.0.0 -p "${PORT:-3000}"
