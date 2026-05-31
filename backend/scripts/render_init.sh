#!/bin/bash
set -e  # Exit on error

echo "=== Starting Render init script ==="

# Convert Render's postgres:// URL to postgresql+asyncpg:// for SQLAlchemy async
if [ -n "$DATABASE_URL" ]; then
  echo "Converting DATABASE_URL for async/sync drivers..."
  # For Alembic migrations, use sync driver (psycopg2)
  export ALEMBIC_DATABASE_URL="${DATABASE_URL/postgres:\/\//postgresql:\/\/}"
  echo "ALEMBIC_DATABASE_URL: ${ALEMBIC_DATABASE_URL%%:*}://***"
  # For FastAPI app, use async driver (asyncpg)
  export DATABASE_URL="${DATABASE_URL/postgres:\/\//postgresql+asyncpg:\/\/}"
  echo "DATABASE_URL: ${DATABASE_URL%%:*}://***"
else
  echo "ERROR: DATABASE_URL not set!"
  exit 1
fi

# Run migrations with sync URL
echo "=== Running Alembic migrations ==="
alembic upgrade head || {
  echo "ERROR: Alembic migrations failed!"
  exit 1
}
echo "=== Migrations completed successfully ==="

# Start the app with async URL
echo "=== Starting Uvicorn ==="
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
