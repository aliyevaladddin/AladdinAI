#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

VENV=".venv"
if [ ! -x "$VENV/bin/alembic" ]; then
  echo "[migrate] alembic not found in $VENV — run scripts/install.sh first" >&2
  exit 1
fi

cd backend
exec "../$VENV/bin/alembic" "${@:-upgrade head}"
