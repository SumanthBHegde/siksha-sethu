#!/usr/bin/env bash
# Launch backend (port 8000) and frontend (port 5173) together.
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

# Backend
(cd "$ROOT/backend" && ./run.sh) &
BACKEND_PID=$!

# Frontend
(cd "$ROOT/frontend" && ./run.sh) &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
