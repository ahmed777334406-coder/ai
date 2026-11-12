#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ ! -d "$ROOT/frontend/node_modules" ]]; then echo "Frontend dependencies are missing. Run: make install"; exit 1; fi
if [[ -x "$ROOT/.venv/bin/uvicorn" ]]; then UVICORN="$ROOT/.venv/bin/uvicorn"; else UVICORN="uvicorn"; fi
cd "$ROOT"
PYTHONPATH="$ROOT/backend" "$UVICORN" app.main:app --app-dir "$ROOT/backend" --reload --port 8000 & BACK_PID=$!
(cd "$ROOT/frontend" && npm run dev) & FRONT_PID=$!
trap 'kill "$BACK_PID" "$FRONT_PID" 2>/dev/null || true' EXIT INT TERM
wait "$BACK_PID" "$FRONT_PID"
