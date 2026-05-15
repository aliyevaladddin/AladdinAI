"""Outbound messaging tools.

`send_image` lets an agent reply with a picture. The agent supplies only
the `filename` (and an optional caption) — the *channel* and *recipient*
come from `ToolContext.extra`, populated by whichever surface invoked the
runner (orchestrator for Telegram/WhatsApp, chat router for the web).

This keeps the tool surface identical across channels: every agent has
one tool to send images, regardless of how the user reached them. Adding
a new channel means handling one more branch here, not changing agent
configs.
"""
from __future__ import annotations

import logging

from sqlalchemy import select

from app.models.messaging_channel import MessagingChannel
from app.services import media as media_service
from app.tools.base import ToolContext, tool

log = logging.getLogger(__name__)


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
async def send_image(
    ctx: ToolContext,
    filename: str,
    caption: str | None = None,
) -> dict:
    path = media_service.resolve(filename)
    if not path:
        return {"error": f"File {filename!r} not found in media store"}

    channel_type = ctx.extra.get("channel_type")
    if not channel_type:
        return {"error": "No channel in context — agent cannot send images here"}

    # Web chat: queue the attachment for the response payload.
    if channel_type == "web":
        outgoing = ctx.extra.setdefault("outgoing_attachments", [])
        outgoing.append({
            "filename": filename,
            "path": str(path),
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

            await send_telegram_photo(channel, str(recipient), str(path), caption=caption)
            return {"status": "sent", "channel": "telegram", "filename": filename}
        return {"error": f"send_image not implemented for channel {channel_type!r}"}
    except Exception as e:  # noqa: BLE001
        log.exception("send_image failed for channel=%s file=%s", channel_id, filename)
        return {"error": str(e)}
