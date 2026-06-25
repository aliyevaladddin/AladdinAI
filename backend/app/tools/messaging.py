# NOTICE: This file is protected under RCF-PL
"""Outbound messaging tools.

`send_image` lets an agent reply with a picture. The agent supplies only
the `filename` (and an optional caption) — the *channel* and *recipient*
come from `ToolContext.extra`, populated by whichever surface invoked the
runner (orchestrator for Telegram/WhatsApp, chat router for the web).

`send_email` lets an agent send emails via SMTP. The agent provides the
recipient address, subject, and body. The email account is selected from
the user's configured accounts (defaults to the first active one).

This keeps the tool surface identical across channels: every agent has
one tool to send images, regardless of how the user reached them. Adding
a new channel means handling one more branch here, not changing agent
configs.
"""
from __future__ import annotations

import logging

from sqlalchemy import select

from app.models.messaging_channel import MessagingChannel
from app.models.email_account import EmailAccount
from app.services import media_storage
from app.tools.base import ToolContext, tool

log = logging.getLogger(__name__)


# [RCF:PROTECTED]
@tool(
    name="send_image",
    description=(
        "Reply to the user with an image file. Pass the `filename` (UUID.ext) "
        "of an image already in the media store — typically one the user just "
        "sent (its name appears in the system note about attachments). "
        "Add an optional `caption` for accompanying text."
    ),
    parameters={
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Filename inside the media store (UUID.ext). No paths.",
            },
            "caption": {
                "type": "string",
                "description": "Optional text caption to accompany the image.",
            },
        },
        "required": ["filename"],
    },
)
# [RCF:PROTECTED]
async def send_image(
    ctx: ToolContext,
    filename: str,
    caption: str | None = None,
) -> dict:
    # `filename` (UUID.ext) is the backend-agnostic handle. Resolve it to the
    # concrete per-backend handle (disk path for local, GridFS file_id for
    # mongodb) so the file can be located/read regardless of storage backend.
    handle = await media_storage.resolve(ctx.db, ctx.user_id, filename)
    if not handle:
        return {"error": f"File {filename!r} not found in media store"}

    channel_type = ctx.extra.get("channel_type")
    if not channel_type:
        return {"error": "No channel in context — agent cannot send images here"}

    # Web chat: queue the attachment for the response payload. The frontend
    # fetches it via /chat/media/{filename}, so `filename` is the load-bearing
    # key; `file_id` carries the per-backend handle for completeness.
    if channel_type == "web":
        outgoing = ctx.extra.setdefault("outgoing_attachments", [])
        outgoing.append({
            "filename": filename,
            "file_id": handle,
            "mime": "image/jpeg",
            "kind": "image",
            "caption": caption,
        })
        return {"status": "queued", "channel": "web", "filename": filename}

    # Messaging channels: load the channel row and dispatch.
    channel_id = ctx.extra.get("channel_id")
    recipient = ctx.extra.get("recipient")
    if channel_id is None or not recipient:
        return {"error": "Channel context incomplete (channel_id/recipient missing)"}

    channel = (await ctx.db.execute(
        select(MessagingChannel).where(
            MessagingChannel.id == int(channel_id),
            MessagingChannel.user_id == ctx.user_id,
        )
    )).scalar_one_or_none()
    if not channel:
        return {"error": f"Channel {channel_id} not found"}

    try:
        if channel_type == "telegram":
            from app.services.messaging_service import send_telegram_photo

            # send_telegram_photo uploads from a real on-disk path. For local
            # storage the resolved handle *is* such a path. For mongodb there is
            # no file on disk, so materialise the GridFS bytes into a temp file
            # for the duration of the upload, then clean it up.
            import os
            from pathlib import Path

            if Path(handle).exists():
                await send_telegram_photo(channel, str(recipient), handle, caption=caption)
            else:
                data = await media_storage.get_bytes(ctx.db, ctx.user_id, handle)
                if not data:
                    return {"error": f"Failed to read {filename!r} from media store"}
                import tempfile
                suffix = os.path.splitext(filename)[1] or ".bin"
                tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
                try:
                    tmp.write(data)
                    tmp.close()
                    await send_telegram_photo(channel, str(recipient), tmp.name, caption=caption)
                finally:
                    try:
                        os.unlink(tmp.name)
                    except OSError:
                        pass
            return {"status": "sent", "channel": "telegram", "filename": filename}
        return {"error": f"send_image not implemented for channel {channel_type!r}"}
    except Exception as e:  # noqa: BLE001
        log.exception("send_image failed for channel=%s file=%s", channel_id, filename)
        return {"error": str(e)}


# [RCF:PROTECTED]
@tool(
    name="send_email",
    description=(
        "Send an email to a specified recipient. Use this when the user asks you "
        "to send an email, compose a message, or contact someone via email. "
        "Provide the recipient's email address, subject line, and email body."
    ),
    parameters={
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Recipient email address (e.g., user@example.com)",
            },
            "subject": {
                "type": "string",
                "description": "Email subject line",
            },
            "body": {
                "type": "string",
                "description": "Email body content (plain text)",
            },
        },
        "required": ["to", "subject", "body"],
    },
)
# [RCF:PROTECTED]
async def send_email(
    ctx: ToolContext,
    to: str,
    subject: str,
    body: str,
) -> dict:
    """Send an email via the user's configured email account."""
    import re
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", to.strip()):
        return {"error": f"Invalid recipient email address: {to!r}"}
    # Find the user's first active email account
    result = await ctx.db.execute(
        select(EmailAccount)
        .where(
            EmailAccount.user_id == ctx.user_id,
            EmailAccount.status == "connected",
        )
        .order_by(EmailAccount.id)
        .limit(1)
    )
    account = result.scalar_one_or_none()

    if not account:
        return {
            "error": "No email account configured. Please connect an email account in Settings → Email."
        }

    try:
        from app.services.email_service import send_email as send_email_service

        await send_email_service(
            db=ctx.db,
            account=account,
            to_email=to,
            subject=subject,
            body=body,
            contact_id=None,
        )

        return {
            "status": "sent",
            "to": to,
            "subject": subject,
            "from": account.email,
        }
    except Exception as e:  # noqa: BLE001
        log.exception("send_email failed for user=%s to=%s", ctx.user_id, to)
        return {"error": f"Failed to send email: {str(e)}"}
