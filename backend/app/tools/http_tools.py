# NOTICE: This file is protected under RCF-PL
"""HTTP & API tools for AladdinAI.

Provides generic HTTP GET, POST, PUT, DELETE and API call capabilities
for autonomous agent web interactions.
"""
import logging

import httpx

from app.services.url_safety import UnsafeURLError, assert_safe_agent_url
from app.tools.base import ToolContext, tool

log = logging.getLogger(__name__)


def _ssrf_error(url: str, exc: UnsafeURLError) -> dict:
    """Uniform tool-level rejection for unsafe URLs (no 500s to the LLM)."""
    log.warning("Agent HTTP tool blocked unsafe URL %s: %s", url, exc)
    return {
        "error": f"Blocked by SSRF protection: {exc}. "
        "Only public internet URLs are allowed from agent tools.",
        "url": url,
    }


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
        url = assert_safe_agent_url(url)
    except UnsafeURLError as e:
        return _ssrf_error(url, e)
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            resp = await client.get(url, headers=headers or {})
            # Follow redirect hops manually: every hop must re-pass the SSRF
            # check, otherwise a public URL that 302s to 169.254.169.254
            # becomes an exfiltration primitive.
            for _ in range(5):
                if resp.is_redirect:
                    next_url = str(resp.next_request.url)
                    try:
                        next_url = assert_safe_agent_url(next_url)
                    except UnsafeURLError as e:
                        return _ssrf_error(next_url, e)
                    resp = await client.get(next_url, headers=headers or {})
                else:
                    break
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
        url = assert_safe_agent_url(url)
    except UnsafeURLError as e:
        return _ssrf_error(url, e)
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=False) as client:
            resp = await client.post(url, json=json_data or {}, headers=headers or {})
            # Same manual redirect handling as http_get: re-validate each hop.
            for _ in range(5):
                if resp.is_redirect:
                    next_url = str(resp.next_request.url)
                    try:
                        next_url = assert_safe_agent_url(next_url)
                    except UnsafeURLError as e:
                        return _ssrf_error(next_url, e)
                    resp = await client.post(next_url, json=json_data or {}, headers=headers or {})
                else:
                    break
            is_json = "application/json" in resp.headers.get("content-type", "")
            return {
                "status_code": resp.status_code,
                "url": str(resp.url),
                "data": resp.json() if is_json else resp.text[:4000],
            }
    except Exception as e:
        log.exception("http_post tool error")
        return {"error": f"HTTP POST failed: {str(e)}"}
