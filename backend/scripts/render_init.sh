#!/bin/bash
set -euo pipefail

echo "=== Starting Render init script ==="

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: DATABASE_URL is not set."
  echo "       Set it in Render Dashboard -> AladdinAI -> Environment to the connection"
  echo "       string of a live Postgres instance (Internal or External URL)."
  exit 1
fi

# --- Normalize the URL -------------------------------------------------------
# Providers spell Postgres URLs differently (postgres://, postgresql://,
# postgresql+psycopg2://) and may add libpq-only options such as
# ?sslmode=require / ?channel_binding=require. SQLAlchemy's asyncpg dialect
# forwards every query parameter straight to asyncpg.connect(), which rejects
# both of those with "TypeError: unexpected keyword argument". So:
#   <any postgres scheme>://  ->  postgresql+asyncpg://
#   sslmode=<mode>            ->  ssl=<mode>
#   channel_binding, sslrootcert -> dropped (not supported by asyncpg)
# The host is also resolved up front, so a dead database is reported as one
# actionable line instead of a 90-line SQLAlchemy traceback.
NORMALIZED="$(python3 - <<'PY'
import os
import shlex
import socket
import sys
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

DBAPI_SCHEME = "postgresql+asyncpg"
DROPPED_OPTIONS = {"channel_binding", "sslrootcert"}


def fail(message: str) -> "NoReturn":  # type: ignore[name-defined]
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


raw = os.environ["DATABASE_URL"].strip()
if "://" not in raw:
    fail("DATABASE_URL is not a postgres URL (expected postgresql://user:pass@host:5432/db)")

parts = urlsplit(raw)
host = parts.hostname or ""
if not host:
    fail(
        "DATABASE_URL has no host, so there is nothing to connect to. "
        "Re-copy the connection string from the database dashboard."
    )

# Retry the lookup: a database that is being provisioned, resumed or
# maintained can be briefly missing from DNS.
last_error = None
for attempt in range(1, 6):
    try:
        addresses = sorted({info[4][0] for info in socket.getaddrinfo(host, parts.port or 5432)})
        break
    except socket.gaierror as exc:
        last_error = exc
        print(
            f"DNS lookup for '{host}' failed (attempt {attempt}/5): {exc}",
            file=sys.stderr,
        )
        if attempt < 5:
            time.sleep(3)
else:
    fail(
        f"database host '{host}' does not resolve ({last_error}). "
        "The database was most likely deleted or expired, or DATABASE_URL points at "
        "another provider/region. Render free Postgres expires 30 days after creation "
        "and is deleted 14 days later. Create a non-expiring database and update "
        "DATABASE_URL in Render Dashboard -> AladdinAI -> Environment."
    )

print(f"Database host '{host}' resolves to {', '.join(addresses)}", file=sys.stderr)

params, dropped = [], []
for key, value in parse_qsl(parts.query, keep_blank_values=True):
    lowered = key.lower()
    if lowered == "sslmode":
        params.append(("ssl", value))
    elif lowered in DROPPED_OPTIONS:
        dropped.append(key)
    else:
        params.append((key, value))

if dropped:
    print("Dropped options not supported by asyncpg: " + ", ".join(dropped), file=sys.stderr)

url = urlunsplit(
    (
        DBAPI_SCHEME,
        parts.netloc,
        parts.path,
        urlencode(params),
        parts.fragment,
    )
)
print(f"export DATABASE_URL={shlex.quote(url)}")
print(f"export ALEMBIC_DATABASE_URL={shlex.quote(url)}")
PY
)" || exit 1

eval "$NORMALIZED"
echo "Using driver: postgresql+asyncpg"

# --- Migrations --------------------------------------------------------------
echo "=== Running Alembic migrations ==="
alembic upgrade head || {
  echo "ERROR: Alembic migrations failed!"
  exit 1
}
echo "=== Migrations completed successfully ==="

# --- App ---------------------------------------------------------------------
echo "=== Starting Uvicorn ==="
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
