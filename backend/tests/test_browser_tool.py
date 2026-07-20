# NOTICE: This file is protected under RCF-PL v2.0.3
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from app.services.browser import fetch_url_content
from app.tools.base import ToolContext
from app.tools.browser import fetch_url


@pytest.mark.asyncio
async def test_fetch_url_content_httpx_fallback():
    """Verify URL fetching works with HTTPX fallback."""
    res = await fetch_url_content("https://example.com", use_chromium=False)
    assert res["status"] == 200
    assert "Example Domain" in res["content"] or "Example Domain" in res["title"]
    assert res["method"] == "httpx"


@pytest.mark.asyncio
async def test_fetch_url_chromium_live():
    """Verify URL fetching with Playwright Chromium."""
    res = await fetch_url_content("https://example.com", use_chromium=True)
    assert res["status"] == 200
    assert "Example Domain" in res["content"] or "Example Domain" in res["title"]
    assert res["method"] in ("chromium", "httpx")

@pytest.mark.asyncio
async def test_fetch_url_tool_execution():
    """Verify tool wrapper execution for agents."""
    ctx = ToolContext(db=AsyncMock(), user_id=1)
    res = await fetch_url(ctx, "https://example.com", use_chromium=False)
    assert res["status"] == 200
    assert "url" in res
    assert "content" in res
