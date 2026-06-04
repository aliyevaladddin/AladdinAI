"""Unified media storage interface — auto-switches between local and MongoDB storage.

Backend selection priority:
  1. User's setting in system_settings.media_storage_backend
  2. MEDIA_STORAGE env variable
  3. Default: 'local'

This wrapper provides the same async API for both backends, allowing gradual
migration without breaking existing code.
"""
from __future__ import annotations

import os
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_settings import SystemSettings


async def _backend(db: AsyncSession, user_id: int) -> str:
    """Return 'mongodb' or 'local' based on user settings or env."""
    # First check user settings
    result = await db.execute(
        select(SystemSettings).where(SystemSettings.user_id == user_id)
    )
    settings = result.scalars().first()
    if settings and settings.media_storage_backend:
        return settings.media_storage_backend.lower()

    # Fallback to env variable
    env_backend = os.environ.get("MEDIA_STORAGE", "").lower()
    if env_backend in ("mongodb", "local"):
        return env_backend

    # Default to local
    return "local"


async def save_bytes(
    db: AsyncSession,
    user_id: int,
    data: bytes,
    mime: str | None,
    *,
    original_filename: str | None = None,
) -> dict[str, Any]:
    """Save bytes to storage backend.

    Returns: {file_id/path: str, filename: str, mime: str}
    """
    backend = await _backend(db, user_id)
    if backend == "mongodb":
        from app.services import media_mongo
        return await media_mongo.save_bytes(db, user_id, data, mime, original_filename=original_filename)
    else:
        from app.services import media
        # Legacy API doesn't need db/user_id
        return media.save_bytes(data, mime)


async def get_bytes(
    db: AsyncSession,
    user_id: int,
    file_id: str,
) -> bytes | None:
    """Retrieve file bytes by file_id."""
    backend = await _backend(db, user_id)
    if backend == "mongodb":
        from app.services import media_mongo
        return await media_mongo.get_bytes(db, user_id, file_id)
    else:
        from app.services import media
        # Legacy: file_id is actually filename
        path = media.resolve(file_id)
        return path.read_bytes() if path else None


async def resolve(
    db: AsyncSession,
    user_id: int,
    filename: str,
) -> str | None:
    """Find file_id by filename."""
    backend = await _backend(db, user_id)
    if backend == "mongodb":
        from app.services import media_mongo
        return await media_mongo.resolve(db, user_id, filename)
    else:
        from app.services import media
        path = media.resolve(filename)
        return str(path) if path else None


async def to_data_url(
    db: AsyncSession,
    user_id: int,
    file_id: str,
    mime: str | None = None,
) -> str | None:
    """Read file and return data URL for LLM inline use."""
    backend = await _backend(db, user_id)
    if backend == "mongodb":
        from app.services import media_mongo
        return await media_mongo.to_data_url(db, user_id, file_id, mime)
    else:
        from app.services import media
        # Legacy: file_id is path
        return media.to_data_url(file_id, mime)


async def download_telegram_file(
    db: AsyncSession,
    user_id: int,
    bot_token: str,
    file_id: str,
) -> dict[str, Any] | None:
    """Download Telegram file and save to storage."""
    backend = await _backend(db, user_id)
    if backend == "mongodb":
        from app.services import media_mongo
        return await media_mongo.download_telegram_file(db, user_id, bot_token, file_id)
    else:
        from app.services import media
        # Legacy API doesn't need db/user_id
        return await media.download_telegram_file(bot_token, file_id)


async def delete_file(
    db: AsyncSession,
    user_id: int,
    file_id: str,
) -> bool:
    """Delete file from storage."""
    backend = await _backend(db, user_id)
    if backend == "mongodb":
        from app.services import media_mongo
        return await media_mongo.delete_file(db, user_id, file_id)
    else:
        from app.services import media
        from pathlib import Path
        # Legacy: file_id is filename
        path = media.resolve(file_id)
        if path and path.exists():
            path.unlink()
            return True
        return False
