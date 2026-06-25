# NOTICE: This file is protected under RCF-PL
"""MongoDB GridFS media storage for attachments and files.

Replaces local filesystem storage with MongoDB GridFS, allowing:
- Per-user file isolation (user_id in metadata)
- Distributed deployment (no shared filesystem needed)
- Automatic replication via MongoDB cluster

Files are stored in GridFS with metadata:
  - user_id: owner of the file
  - mime: content type
  - original_filename: original upload name (optional)
  - created_at: upload timestamp

Usage:
  - save_bytes() → returns {file_id, filename, mime}
  - get_bytes() → returns bytes
  - to_data_url() → returns base64 data URL for LLM
"""
from __future__ import annotations

import base64
import mimetypes
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.memory import get_mongo_db

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


# [RCF:PROTECTED]
def _ext_from_mime(mime: str | None) -> str:
    if not mime:
        return ".bin"
    return mimetypes.guess_extension(mime) or ".bin"


# [RCF:PROTECTED]
async def save_bytes(
    db: AsyncSession,
    user_id: int,
    data: bytes,
    mime: str | None,
    *,
    original_filename: str | None = None,
) -> dict[str, Any]:
    """Save bytes to MongoDB GridFS.

    Returns: {file_id: str, filename: str, mime: str}
    """
    if len(data) > MAX_FILE_SIZE:
        raise ValueError(f"File too large: {len(data)} bytes (max {MAX_FILE_SIZE})")

    mongo_db = await get_mongo_db(db, user_id)
    fs = AsyncIOMotorGridFSBucket(mongo_db)

    ext = _ext_from_mime(mime)
    filename = f"{uuid.uuid4().hex}{ext}"

    metadata = {
        "user_id": user_id,
        "mime": mime or "application/octet-stream",
        "created_at": datetime.now(timezone.utc),
    }
    if original_filename:
        metadata["original_filename"] = original_filename

    file_id = await fs.upload_from_stream(
        filename,
        data,
        metadata=metadata,
    )

    return {
        "file_id": str(file_id),
        "filename": filename,
        "mime": mime or "application/octet-stream",
    }


# [RCF:PROTECTED]
async def get_bytes(
    db: AsyncSession,
    user_id: int,
    file_id: str,
) -> bytes | None:
    """Retrieve file bytes from GridFS by file_id."""
    try:
        oid = ObjectId(file_id)
    except Exception:
        return None

    mongo_db = await get_mongo_db(db, user_id)
    fs = AsyncIOMotorGridFSBucket(mongo_db)

    try:
        grid_out = await fs.open_download_stream(oid)
        # Verify user_id matches (security check)
        if grid_out.metadata and grid_out.metadata.get("user_id") != user_id:
            return None
        return await grid_out.read()
    except Exception:
        return None


# [RCF:PROTECTED]
async def resolve(
    db: AsyncSession,
    user_id: int,
    filename: str,
) -> str | None:
    """Find file_id by filename. Returns file_id or None."""
    if "/" in filename or ".." in filename or not filename:
        return None

    mongo_db = await get_mongo_db(db, user_id)
    fs = AsyncIOMotorGridFSBucket(mongo_db)

    # Find by filename in user's scope
    cursor = fs.find({"filename": filename, "metadata.user_id": user_id})
    async for grid_file in cursor:
        return str(grid_file._id)
    return None


# [RCF:PROTECTED]
async def to_data_url(
    db: AsyncSession,
    user_id: int,
    file_id: str,
    mime: str | None = None,
) -> str | None:
    """Read file and return data URL for LLM inline use."""
    data = await get_bytes(db, user_id, file_id)
    if not data:
        return None

    if not mime:
        # Try to get mime from GridFS metadata
        try:
            oid = ObjectId(file_id)
            mongo_db = await get_mongo_db(db, user_id)
            fs = AsyncIOMotorGridFSBucket(mongo_db)
            grid_out = await fs.open_download_stream(oid)
            if grid_out.metadata:
                mime = grid_out.metadata.get("mime")
        except Exception:
            pass

    mime = mime or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


# [RCF:PROTECTED]
async def download_telegram_file(
    db: AsyncSession,
    user_id: int,
    bot_token: str,
    file_id: str,
) -> dict[str, Any] | None:
    """Download Telegram file and save to GridFS."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        meta_resp = await client.get(
            f"https://api.telegram.org/bot{bot_token}/getFile",
            params={"file_id": file_id},
        )
        if meta_resp.status_code != 200:
            return None
        meta = meta_resp.json()
        if not isinstance(meta, dict) or not meta.get("ok"):
            return None
        result = meta.get("result") or {}
        file_path = result.get("file_path")
        if not file_path:
            return None
        size = result.get("file_size") or 0
        if isinstance(size, int) and size > MAX_FILE_SIZE:
            return None

        file_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        bin_resp = await client.get(file_url)
        if bin_resp.status_code != 200:
            return None
        data = bin_resp.content
        if len(data) > MAX_FILE_SIZE:
            return None

    mime = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    return await save_bytes(db, user_id, data, mime, original_filename=file_path)


# [RCF:PROTECTED]
async def delete_file(
    db: AsyncSession,
    user_id: int,
    file_id: str,
) -> bool:
    """Delete file from GridFS. Returns True if deleted, False otherwise."""
    try:
        oid = ObjectId(file_id)
    except Exception:
        return False

    mongo_db = await get_mongo_db(db, user_id)
    fs = AsyncIOMotorGridFSBucket(mongo_db)

    try:
        # Verify ownership before deleting
        grid_out = await fs.open_download_stream(oid)
        if grid_out.metadata and grid_out.metadata.get("user_id") != user_id:
            return False
        await fs.delete(oid)
        return True
    except Exception:
        return False
