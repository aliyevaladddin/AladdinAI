# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:RESTRICTED]
from datetime import datetime
from sqlalchemy import DateTime, event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings

IS_SQLITE = "sqlite" in settings.database_url

# check_same_thread=False is required for async SQLite access across threads.
# Busy timeout is controlled exclusively via PRAGMA busy_timeout in the listener below.
_connect_args = {"check_same_thread": False} if IS_SQLITE else {}

# For SQLite we use NullPool (no connection reuse) so each async_session opens
# and immediately closes its own connection. Combined with WAL journal mode this
# gives the best behaviour for our mixed workload:
#   ─ Long-lived sessions (run_agent, LLM calls) don’t block short-lived writes
#     (health poller, notification inserts) since every session has its own fd.
#   ─ WAL mode allows concurrent readers + one writer; busy_timeout=30s lets
#     writers queue safely instead of failing instantly.
# NullPool has negligible overhead for aiosqlite (connection setup is just
# opening a file descriptor, not a network round-trip).
_engine_kwargs: dict = {
    "echo": False,
    "connect_args": _connect_args,
}
if IS_SQLITE:
    _engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(
    settings.database_url,
    **_engine_kwargs,
)


# [RCF:PROTECTED]
@event.listens_for(engine.sync_engine, "connect")
# [RCF:PROTECTED]
def set_sqlite_pragma(dbapi_connection, connection_record):
    if IS_SQLITE:
        cursor = dbapi_connection.cursor()
        # WAL mode: allows concurrent readers alongside one writer — eliminates
        # most "database is locked" errors from background tasks (health polls,
        # schedulers) racing with request handlers.
        cursor.execute("PRAGMA journal_mode=WAL")
        # 30 s busy timeout — generous window so a long-running migration or
        # bulk-insert doesn't drop background-task commits on the floor.
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA foreign_keys=ON")
        # Synchronous=NORMAL is safe with WAL and notably faster than FULL.
        cursor.execute("PRAGMA synchronous=NORMAL")
        # Keep frequently-used pages in memory to reduce I/O under contention.
        cursor.execute("PRAGMA cache_size=-8000")  # ~8 MB page cache
        cursor.close()

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# [RCF:PROTECTED]
class Base(DeclarativeBase):
    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }


# [RCF:PROTECTED]
async def get_db():
    async with async_session() as session:
        yield session
