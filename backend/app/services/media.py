"""Local media storage + helpers for image attachments.

Files live in `backend/media/attachments/` (same dir email attachments use).
Filenames are UUIDs + the original extension so two users can't collide.

This module is intentionally tiny — it just knows where files live, how to
save bytes, how to load them back as base64 data URIs (for inline LLM use),
and how to download a Telegram file_id to disk.
"""
from __future__ import annotations

import base64
import mimetypes
import uuid
from pathlib import Path
from typing import Any

import httpx

MEDIA_ROOT = Path(__file__).resolve().parents[2] / "media" / "attachments"
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

MAX_TELEGRAM_FILE_BYTES = 20 * 1024 * 1024  # 20MB — Telegram's getFile limit


def _ext_from_mime(mime: str | None) -> str:
    if not mime:
        return ".bin"
    return mimetypes.guess_extension(mime) or ".bin"


def save_bytes(data: bytes, mime: str | None) -> dict[str, Any]:
    """Persist bytes to MEDIA_ROOT, return {path, filename, mime}."""
    ext = _ext_from_mime(mime)
    filename = f"{uuid.uuid4().hex}{ext}"
    path = MEDIA_ROOT / filename
    path.write_bytes(data)
    return {"path": str(path), "filename": filename, "mime": mime or "application/octet-stream"}


def resolve(filename: str) -> Path | None:
    """Resolve a filename inside MEDIA_ROOT, refusing path traversal."""
    if "/" in filename or ".." in filename or not filename:
        return None
    p = MEDIA_ROOT / filename
    try:
        p = p.resolve()
        if MEDIA_ROOT.resolve() not in p.parents and p != MEDIA_ROOT.resolve():
            return None
    except OSError:
        return None
    return p if p.exists() else None


def read_path(path: str | Path) -> bytes | None:
    """Read bytes from an absolute path, but only if it lives inside MEDIA_ROOT.

    Used to load back a handle produced by ``resolve`` (which returns a full
    path) without re-running the filename guard. The MEDIA_ROOT containment
    check keeps path traversal out even though we accept an absolute path.
    """
    try:
        p = Path(path).resolve()
        root = MEDIA_ROOT.resolve()
        if root not in p.parents and p != root:
            return None
        return p.read_bytes() if p.exists() else None
    except OSError:
        return None


def to_data_url(path: str | Path, mime: str | None = None) -> str:
    """Read a file and return a `data:<mime>;base64,...` string for LLM inline use."""
    p = Path(path)
    data = p.read_bytes()
    if not mime:
        mime, _ = mimetypes.guess_type(str(p))
        mime = mime or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


async def download_telegram_file(bot_token: str, file_id: str) -> dict[str, Any] | None:
    """getFile → download → save under MEDIA_ROOT. Returns {path, filename, mime} or None."""
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
        if isinstance(size, int) and size > MAX_TELEGRAM_FILE_BYTES:
            return None

        file_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        bin_resp = await client.get(file_url)
        if bin_resp.status_code != 200:
            return None
        data = bin_resp.content
        if len(data) > MAX_TELEGRAM_FILE_BYTES:
            return None

    mime = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    return save_bytes(data, mime)
