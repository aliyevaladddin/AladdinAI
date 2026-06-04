"""Image generation tool.

`generate_image` lets any agent create a NEW picture from a text prompt and
deliver it to the user. It mirrors `send_image` (app/tools/messaging.py): the
agent supplies only the description, while the channel/recipient come from
`ToolContext.extra`. The generated file is persisted with the same
`media_service.save_bytes` helper and queued/dispatched through the identical
outgoing-attachment contract, so the web frontend renders it with no changes.

Generation runs on the calling agent's own provider (NIM hosts both chat and
image models under one API key) via `services.image_gen`.
"""
from __future__ import annotations

import logging

from sqlalchemy import select

from app.models.agent import Agent
from app.models.llm_provider import LLMProvider
from app.models.messaging_channel import MessagingChannel
from app.services import image_gen, media_storage
from app.services.llm_service import LLMError
from app.tools.base import ToolContext, tool

log = logging.getLogger(__name__)


@tool(
    name="generate_image",
    description=(
        "Create a NEW image from a text description and send it to the user. "
        "Use this whenever the user asks you to draw, generate, paint, or make "
        "a picture/illustration/logo. Pass a vivid, detailed `prompt` "
        "describing what to render. The image is created and delivered "
        "automatically — you do not need to call send_image afterwards."
    ),
    parameters={
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Detailed description of the image to generate.",
            },
        },
        "required": ["prompt"],
    },
)
async def generate_image(ctx: ToolContext, prompt: str) -> dict:
    prompt = (prompt or "").strip()
    if not prompt:
        return {"error": "prompt is required and must be non-empty"}

    if ctx.agent_id is None:
        return {"error": "No calling agent in context"}
    agent = (await ctx.db.execute(
        select(Agent).where(Agent.id == ctx.agent_id)
    )).scalar_one_or_none()
    if not agent or not agent.llm_provider_id:
        return {"error": "Calling agent has no LLM provider"}
    provider = (await ctx.db.execute(
        select(LLMProvider).where(LLMProvider.id == agent.llm_provider_id)
    )).scalar_one_or_none()
    if not provider:
        return {"error": "Provider not found"}

    try:
        img_bytes, mime = await image_gen.generate_image_bytes(provider, prompt)
    except LLMError as e:
        log.warning("generate_image failed for agent %s: %s", ctx.agent_id, e)
        return {"error": str(e)}

    saved = await media_storage.save_bytes(ctx.db, ctx.user_id, img_bytes, mime)

    channel_type = ctx.extra.get("channel_type")
    if not channel_type:
        # No delivery channel — still report the stored file so the agent can
        # reference it, but it won't be auto-delivered.
        return {"status": "generated", "filename": saved["filename"]}

    # Web chat: queue the attachment for the response payload (same shape as send_image).
    if channel_type == "web":
        outgoing = ctx.extra.setdefault("outgoing_attachments", [])
        outgoing.append({
            "filename": saved["filename"],
            "file_id": saved.get("file_id", saved.get("path")),  # Support both backends
            "mime": saved["mime"],
            "kind": "image",
            "caption": prompt,
        })
        return {"status": "generated", "channel": "web", "filename": saved["filename"]}

    # Messaging channels: dispatch immediately.
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

            # Get file bytes for telegram
            file_bytes = await media_storage.get_bytes(ctx.db, ctx.user_id, saved.get("file_id", saved.get("path", "")))
            if not file_bytes:
                return {"error": "Failed to retrieve generated image"}

            # TODO: Update send_telegram_photo to accept bytes instead of path
            # For now, we need to pass the file_id/path
            await send_telegram_photo(channel, str(recipient), saved.get("file_id", saved.get("path", "")), caption=prompt)
            return {"status": "sent", "channel": "telegram", "filename": saved["filename"]}
        return {"error": f"generate_image not implemented for channel {channel_type!r}"}
    except Exception as e:  # noqa: BLE001
        log.exception("generate_image dispatch failed for channel=%s", channel_id)
        return {"error": str(e)}
