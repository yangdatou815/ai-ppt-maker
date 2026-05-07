#!/usr/bin/env bash
# Local dev launcher: starts backend (uvicorn) + frontend (vite) in parallel.
set -euo pipefail
cd "$(dirname "$0")/.."

cleanup() {
  jobs -p | xargs -r kill 2>/dev/null || true
}
trap cleanup EXIT INT TERM

(
  cd backend
  if [[ ! -d .venv ]]; then
    python3 -m venv .venv
    .venv/bin/pip install -e ".[dev]"
  fi
  exec .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port "${APP_PORT:-8080}"
) &

(
  cd frontend
  if [[ ! -d node_modules ]]; then
    npm install
  fi
  exec npm run dev
) &

wait
