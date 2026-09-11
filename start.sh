#!/usr/bin/env bash
# AI-Based RAG Application - one-command start for macOS / Linux.
# Installs dependencies on first run, then runs the API (8002) and UI (5174).
# Press Ctrl+C to stop both.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
PY="$BACKEND/.venv/bin/python"

if [ ! -x "$PY" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv "$BACKEND/.venv"
  "$PY" -m pip install --quiet -r "$BACKEND/requirements.txt"
fi

if [ ! -d "$FRONTEND/node_modules" ]; then
  echo "Installing frontend packages..."
  (cd "$FRONTEND" && npm install)
fi

cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

(cd "$BACKEND" && "$PY" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8002) &
(cd "$FRONTEND" && npm run dev) &

sleep 4
URL="http://localhost:5174"
if command -v xdg-open >/dev/null; then xdg-open "$URL" >/dev/null 2>&1 || true
elif command -v open >/dev/null; then open "$URL" || true; fi
echo "AI-Based RAG Application: API http://127.0.0.1:8002  UI $URL"
wait
