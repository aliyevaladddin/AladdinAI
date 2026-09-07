# NOTICE: This file is protected under RCF-PL v2.0.3
"""SSRF protection tests for agent HTTP tools.

The agent-reachable tools (http_get, http_post, fetch_url) must never fetch
internal addresses — a message-injected instruction pointing the agent at
169.254.169.254 or 10.x.x.x would otherwise become a credential exfiltration
primitive. These tests pin that behavior at the tool boundary.
"""
from __future__ import annotations

import importlib
from unittest.mock import AsyncMock

import pytest

import app.services.url_safety as url_safety
from app.tools.base import ToolContext
from app.tools.browser import fetch_url
from app.tools.http_tools import http_get, http_post


@pytest.fixture(autouse=True)
def strict_ssrf(monkeypatch):
    """Tests must run with SSRF protection fully on, regardless of dev .env.

    url_safety reads the env flags at import time; reload the module under
    forced-strict env so the dev ALLOW_PRIVATE_URLS=true in this
    environment's .env doesn't neuter the tests. http_tools/browser import
    `assert_safe_agent_url` by reference, so re-point them after the reload.
    """
    monkeypatch.setenv("ALLOW_LOCALHOST_URLS", "false")
    monkeypatch.setenv("ALLOW_PRIVATE_URLS", "false")
    import app.services.browser as browser_service
    import app.tools.http_tools as http_tools

    reloaded = importlib.reload(url_safety)
    monkeypatch.setattr(http_tools, "assert_safe_agent_url", reloaded.assert_safe_agent_url)
    monkeypatch.setattr(http_tools, "UnsafeURLError", reloaded.UnsafeURLError)
    monkeypatch.setattr(browser_service, "assert_safe_agent_url", reloaded.assert_safe_agent_url)
    monkeypatch.setattr(browser_service, "UnsafeURLError", reloaded.UnsafeURLError)
    yield
    importlib.reload(url_safety)  # restore module to the ambient env state


@pytest.fixture
def ctx() -> ToolContext:
    return ToolContext(db=AsyncMock(), user_id=1)


BLOCKED_URLS = [
    "http://127.0.0.1/admin",
    "http://localhost:8080/api",
    "http://169.254.169.254/latest/meta-data/",
    "http://10.0.0.5/internal",
    "http://192.168.1.1/router",
    "http://172.16.0.1/service",
    "http://[::1]/port6379",
    "http://0.0.0.0/",
    "file:///etc/passwd",
    "ftp://example.com/file",
    "http://user:secret@example.com/page",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("url", BLOCKED_URLS)
async def test_http_get_blocks_private_and_malformed_urls(ctx: ToolContext, url: str):
    res = await http_get(ctx, url)
    assert res.get("error", "").startswith("Blocked by SSRF protection"), f"{url} not blocked: {res}"


@pytest.mark.asyncio
@pytest.mark.parametrize("url", BLOCKED_URLS)
async def test_http_post_blocks_private_and_malformed_urls(ctx: ToolContext, url: str):
    res = await http_post(ctx, url, json_data={"a": 1})
    assert res.get("error", "").startswith("Blocked by SSRF protection"), f"{url} not blocked: {res}"


@pytest.mark.asyncio
async def test_http_get_blocked_before_any_network_call(ctx: ToolContext, monkeypatch):
    """A blocked URL must be rejected before a socket is opened."""
    called = False

    class _Boom:
        def __call__(self, *args, **kwargs):
            nonlocal called
            called = True
            raise AssertionError("network client was constructed for a blocked URL")

    monkeypatch.setattr("app.tools.http_tools.httpx.AsyncClient", _Boom())
    res = await http_get(ctx, "http://169.254.169.254/latest/meta-data/")
    assert res.get("error", "").startswith("Blocked by SSRF protection")
    assert not called


@pytest.mark.asyncio
async def test_http_get_redirect_to_private_is_blocked(ctx: ToolContext, monkeypatch):
    """A public URL that redirects to an internal address must be stopped.

    DNS is mocked too: the sandbox has no real resolver, and the test targets
    the redirect-hop validation, not the initial DNS check.
    """

    def fake_getaddrinfo(host, *a, **kw):
        if host == "169.254.169.254":
            return [(2, 1, 6, "", ("169.254.169.254", 0))]
        return [(2, 1, 6, "", ("8.8.8.8", 0))]  # public resolver

    monkeypatch.setattr("app.services.url_safety.socket.getaddrinfo", fake_getaddrinfo)

    class FakeResponse:
        def __init__(self, status_code, headers, location):
            self.status_code = status_code
            self.headers = headers
            self.is_redirect = status_code in (301, 302, 303, 307, 308)
            self._location = location

        @property
        def next_request(self):
            import httpx

            return type("Req", (), {"url": httpx.URL(self._location)})()

    class FakeClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, headers=None):
            if "public.example.com" in str(url):
                return FakeResponse(302, {}, "http://169.254.169.254/latest/meta-data/")
            return FakeResponse(200, {"content-type": "text/plain"}, "")

    monkeypatch.setattr("app.tools.http_tools.httpx.AsyncClient", FakeClient)
    res = await http_get(ctx, "https://public.example.com/redirect")
    assert res.get("error", "").startswith("Blocked by SSRF protection"), res
    assert "169.254" in str(res) or "non-routable" in str(res), res


@pytest.mark.asyncio
async def test_fetch_url_content_blocks_private(monkeypatch):
    from app.services.browser import fetch_url_content

    res = await fetch_url_content("http://169.254.169.254/latest/meta-data/", use_chromium=False)
    assert res["method"] == "failed"
    assert res["status"] == 403
    assert "SSRF protection" in res["content"]


@pytest.mark.asyncio
async def test_fetch_url_tool_surfaces_block(ctx: ToolContext):
    res = await fetch_url(ctx, "http://127.0.0.1:8000/ready", use_chromium=False)
    assert res["method"] == "failed"
    assert "SSRF protection" in res["content"]


@pytest.mark.asyncio
async def test_http_get_allows_public_url(ctx: ToolContext, monkeypatch):
    """Public URLs still work end-to-end (mocked network + DNS)."""

    def fake_getaddrinfo(host, *a, **kw):
        return [(2, 1, 6, "", ("8.8.8.8", 0))]  # public resolver

    monkeypatch.setattr("app.services.url_safety.socket.getaddrinfo", fake_getaddrinfo)
    class FakeResponse:
        status_code = 200
        is_redirect = False
        headers = {"content-type": "application/json"}

        @property
        def url(self):
            import httpx

            return httpx.URL("https://api.public.example.com/zen")

        def json(self):
            return {"ok": True}

    class FakeClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, headers=None):
            return FakeResponse()

    monkeypatch.setattr("app.tools.http_tools.httpx.AsyncClient", FakeClient)
    res = await http_get(ctx, "https://api.public.example.com/zen")
    assert res["status_code"] == 200
    assert res["data"] == {"ok": True}
