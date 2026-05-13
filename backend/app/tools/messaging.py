"""Outbound messaging tools.

`send_image` lets an agent push an image file (already stored under
`media/attachments/`) back to a user via a messaging channel. The agent
references the image by `filename` — the same name that was returned by
the upload endpoint or saved during inbound media download. Path-traversal
is blocked by `media.resolve`; the channel is scoped to `ctx.user_id` so
an agent cannot reach across tenants.
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
        "Send an image file back to the user via a messaging channel. "
        "Use this when you want to reply with a picture (e.g. a reference "
        "photo of a healthy plant leaf). The image must already exist in "
        "the media store — pass its `filename` (UUID.ext), not a full path."
    ),
    parameters={
        "type": "object",
        "properties": {
            "channel_id": {
                "type": "integer",
                "description": "ID of the MessagingChannel to send through.",
            },
            "to": {
                "type": "string",
                "description": "Recipient identifier — Telegram chat_id, WhatsApp phone, etc.",
            },
            "filename": {
                "type": "string",
                "description": "Filename inside media/attachments (UUID.ext). No paths.",
            },
            "caption": {
                "type": "string",
                "description": "Optional text caption sent alongside the image.",
            },
        },
        "required": ["channel_id", "to", "filename"],
    },
)
async def send_image(
    ctx: ToolContext,
    channel_id: int,
    to: str,
    filename: str,
    caption: str | None = None,
) -> dict:
    try:
        channel_id_int = int(channel_id)
    except (TypeError, ValueError):
        return {"error": f"Invalid channel_id: {channel_id!r}"}

    result = await ctx.db.execute(
        select(MessagingChannel).where(
            MessagingChannel.id == channel_id_int,
            MessagingChannel.user_id == ctx.user_id,
        )
    )
    channel = result.scalar_one_or_none()
    if not channel:
        return {"error": f"Channel {channel_id_int} not found"}

    path = media_service.resolve(filename)
    if not path:
        return {"error": f"File {filename!r} not found in media store"}

    ctype = (channel.type or "").lower()
    try:
        if ctype == "telegram":
            from app.services.messaging_service import send_telegram_photo

            await send_telegram_photo(channel, str(to), str(path), caption=caption)
            return {"status": "sent", "channel": "telegram", "filename": filename}
        return {"error": f"send_image not yet implemented for channel type {ctype!r}"}
    except Exception as e:  # noqa: BLE001
        log.exception("send_image failed for channel=%s file=%s", channel_id_int, filename)
        return {"error": str(e)}
