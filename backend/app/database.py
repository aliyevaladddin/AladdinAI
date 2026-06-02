# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:RESTRICTED]
from datetime import datetime
from sqlalchemy import DateTime, event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

_is_sqlite = "sqlite" in settings.database_url

# For SQLite: pass a busy_timeout so concurrent writers wait instead of
# immediately raising OperationalError("database is locked").
_connect_args = {"timeout": 15} if _is_sqlite else {}

engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args=_connect_args,
)


@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if _is_sqlite:
        cursor = dbapi_connection.cursor()
        # WAL mode: allows concurrent readers alongside one writer — eliminates
        # most "database is locked" errors from background tasks (health polls,
        # schedulers) racing with request handlers.
        cursor.execute("PRAGMA journal_mode=WAL")
        # How long (ms) SQLite waits for a lock before raising OperationalError.
        # 10 s is generous; almost all real contention clears within milliseconds.
        cursor.execute("PRAGMA busy_timeout=10000")
        cursor.execute("PRAGMA foreign_keys=ON")
        # Synchronous=NORMAL is safe with WAL and notably faster than FULL.
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }


async def get_db():
    async with async_session() as session:
        yield session
