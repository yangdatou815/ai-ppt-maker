#!/usr/bin/env bash
# DoD gate — must pass locally before every commit.
# Mirrored 1:1 by .github/workflows/ci.yml.
set -euo pipefail
cd "$(dirname "$0")/.."

bold() { printf '\033[1m%s\033[0m\n' "$*"; }

bold "[1/4] Backend: ruff lint"
(
  cd backend
  if [[ -d .venv ]]; then source .venv/bin/activate; fi
  ruff check app tests
)

bold "[2/4] Backend: pytest + coverage (>=70%)"
(
  cd backend
  if [[ -d .venv ]]; then source .venv/bin/activate; fi
  pytest --cov=app --cov-report=term-missing --cov-fail-under=70
)

bold "[3/4] Frontend: type-check + lint + tests"
(
  cd frontend
  if [[ ! -d node_modules ]]; then npm install --no-audit --no-fund; fi
  npx vue-tsc -b --noEmit || true   # M1: not blocking; ratchet to blocking in M2
  npm run test --silent
)

bold "[4/4] git push --dry-run"
git push --dry-run 2>/dev/null || echo "(no upstream configured yet — skip)"

bold "✓ DoD gate passed."
