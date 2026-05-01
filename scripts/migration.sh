#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ $# -lt 1 ]; then
  echo "Usage: scripts/migration.sh \"description of change\"" >&2
  exit 1
fi

cd backend
exec "../.venv/bin/alembic" revision --autogenerate -m "$1"
