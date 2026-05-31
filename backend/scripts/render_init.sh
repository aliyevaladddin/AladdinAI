#!/bin/bash
# Convert Render's postgres:// URL to postgresql+asyncpg:// for SQLAlchemy async
if [ -n "$DATABASE_URL" ]; then
  export DATABASE_URL="${DATABASE_URL/postgres:\/\//postgresql+asyncpg:\/\/}"
fi

# Run migrations
alembic upgrade head

# Start the app
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
