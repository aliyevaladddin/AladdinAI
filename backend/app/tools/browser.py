# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
from __future__ import annotations

import logging
from typing import Any

from app.services.browser import fetch_url_content
from app.tools.base import ToolContext, tool

logger = logging.getLogger(__name__)


# [RCF:PROTECTED]
@tool(
    name="fetch_url",
    description=(
        "Fetch and read the content of any web page / URL using Chromium Headless Browser. "
        "Use this tool whenever the user provides a website URL or link in chat to extract its full text."
    ),
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The web page URL to fetch and read (e.g. https://example.com/article).",
            },
            "use_chromium": {
                "type": "boolean",
                "description": "Whether to use full Chromium JavaScript rendering (default: true).",
                "default": True,
            },
        },
        "required": ["url"],
    },
)
async def fetch_url(
    ctx: ToolContext, url: str, use_chromium: bool = True
) -> dict[str, Any]:
    """Fetch and read web page content for the agent context."""
    logger.info("Agent fetching URL content via Chromium/HTTPX: %s", url)
    res = await fetch_url_content(url, use_chromium=use_chromium)
    return res
