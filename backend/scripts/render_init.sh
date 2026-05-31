#!/bin/bash
# Convert Render's postgres:// URL to postgresql+asyncpg:// for SQLAlchemy async
if [ -n "$DATABASE_URL" ]; then
  # For Alembic migrations, use sync driver (psycopg2)
  export ALEMBIC_DATABASE_URL="${DATABASE_URL/postgres:\/\//postgresql:\/\/}"
  # For FastAPI app, use async driver (asyncpg)
  export DATABASE_URL="${DATABASE_URL/postgres:\/\//postgresql+asyncpg:\/\/}"
fi

# Run migrations with sync URL
alembic upgrade head

# Start the app with async URL
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
