"""Vision tool — let any agent ask a vision model to describe an image.

The agent's own LLM may be text-only (and likely is, so it can use tools).
When a user attaches images, the orchestrator/chat router notes their
filenames in the conversation and exposes this tool — the agent decides
whether to inspect the image and what to ask about it.

The vision model is shared across all agents: same provider as the calling
agent's LLM (NIM hosts both text and vision under one base URL), model id
from `VISION_MODEL` env (default `meta/llama-3.2-11b-vision-instruct`).
"""
from __future__ import annotations

import logging
import os

from sqlalchemy import select

from app.models.agent import Agent
from app.models.llm_provider import LLMProvider
from app.services import media as media_service
from app.services.llm_service import LLMError, chat_completion
from app.tools.base import ToolContext, tool

log = logging.getLogger(__name__)

DEFAULT_VISION_MODEL = "meta/llama-3.2-11b-vision-instruct"


@tool(
    name="analyze_image",
    description=(
        "Look at an image the user has sent and get a textual description. "
        "Use this whenever the user attaches a photo and you need to know "
        "what is in it. Pass the `filename` exactly as listed in the system "
        "note about attachments — never invent one. Optionally pass a "
        "`question` to focus the description (e.g. 'is this leaf healthy?')."
    ),
    parameters={
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Attachment filename (UUID.ext) from the system note.",
            },
            "question": {
                "type": "string",
                "description": "Optional focused question about the image.",
            },
        },
        "required": ["filename"],
    },
)
async def analyze_image(
    ctx: ToolContext,
    filename: str,
    question: str | None = None,
) -> dict:
    path = media_service.resolve(filename)
    if not path:
        return {"error": f"File {filename!r} not found in media store"}

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
        data_url = media_service.to_data_url(str(path))
    except Exception as e:  # noqa: BLE001
        return {"error": f"Failed to read image: {e}"}

    prompt = question or "Describe this image in detail."
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }
    ]

    model = os.environ.get("VISION_MODEL", DEFAULT_VISION_MODEL)
    try:
        res = await chat_completion(provider, model, messages, max_tokens=512)
    except LLMError as e:
        log.warning("analyze_image: vision call failed for %s: %s", filename, e)
        return {"error": str(e)}

    description = (res.get("content") or "").strip()
    return {"filename": filename, "description": description}
