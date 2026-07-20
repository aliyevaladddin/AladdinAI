# NOTICE: This file is protected under RCF-PL
"""HTTP & API tools for AladdinAI.

Provides generic HTTP GET, POST, PUT, DELETE and API call capabilities
for autonomous agent web interactions.
"""
import logging

import httpx

from app.tools.base import ToolContext, tool

log = logging.getLogger(__name__)


# [RCF:PROTECTED]
@tool(
    name="http_get",
    description="Perform an HTTP GET request to fetch raw web data or JSON from a URL.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Target URL (e.g. 'https://api.github.com/zen')."},
            "headers": {"type": "object", "description": "Optional HTTP headers.", "additionalProperties": True},
        },
        "required": ["url"],
    },
)
# [RCF:PROTECTED]
async def http_get(ctx: ToolContext, url: str, headers: dict | None = None) -> dict:
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers or {})
            is_json = "application/json" in resp.headers.get("content-type", "")
            return {
                "status_code": resp.status_code,
                "url": str(resp.url),
                "data": resp.json() if is_json else resp.text[:4000],
            }
    except Exception as e:
        log.exception("http_get tool error")
        return {"error": f"HTTP GET failed: {str(e)}"}


# [RCF:PROTECTED]
@tool(
    name="http_post",
    description="Perform an HTTP POST request to submit JSON data to a URL or API.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Target URL."},
            "json_data": {"type": "object", "description": "JSON body payload.", "additionalProperties": True},
            "headers": {"type": "object", "description": "Optional HTTP headers.", "additionalProperties": True},
        },
        "required": ["url"],
    },
)
# [RCF:PROTECTED]
async def http_post(
    ctx: ToolContext,
    url: str,
    json_data: dict | None = None,
    headers: dict | None = None,
) -> dict:
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.post(url, json=json_data or {}, headers=headers or {})
            is_json = "application/json" in resp.headers.get("content-type", "")
            return {
                "status_code": resp.status_code,
                "url": str(resp.url),
                "data": resp.json() if is_json else resp.text[:4000],
            }
    except Exception as e:
        log.exception("http_post tool error")
        return {"error": f"HTTP POST failed: {str(e)}"}
