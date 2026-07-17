# NOTICE: This file is protected under RCF-PL
"""Tests for the web_search tool.

Covers the pieces that were broken when the file first landed (registration +
a malformed function schema) plus the two search paths (self-hosted service and
the DuckDuckGo HTML fallback) and its error handling — all without real network,
by patching httpx.AsyncClient.
"""
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest

import app.tools  # noqa: F401 — package import registers every tool as in prod
from app.tools.base import REGISTRY, ToolContext
from app.tools.web_search import DuckDuckGoParser, web_search


# ── registration + schema (the two original bugs) ────────────────────────────
def test_web_search_registered_via_package_import():
    assert "web_search" in REGISTRY


def test_web_search_schema_is_valid_function_schema():
    params = REGISTRY["web_search"].openai_schema()["function"]["parameters"]
    assert params["type"] == "object"
    assert "query" in params["properties"]
    assert params["required"] == ["query"]


# ── DuckDuckGo HTML parser (pure) ────────────────────────────────────────────
def test_ddg_parser_extracts_results():
    html = """
    <div class="result">
      <a class="result__a" href="https://example.com/a">First Title</a>
      <a class="result__snippet" href="https://example.com/a">First snippet text</a>
    </div>
    <div class="result">
      <a class="result__a" href="https://example.com/b">Second Title</a>
      <a class="result__snippet">Second snippet</a>
    </div>
    """
    parser = DuckDuckGoParser()
    parser.feed(html)
    results = parser.get_results()
    assert len(results) == 2
    assert results[0]["title"] == "First Title"
    assert results[0]["link"] == "https://example.com/a"
    assert results[0]["snippet"] == "First snippet text"


def test_ddg_parser_drops_results_without_title_or_link():
    # A result container with no title/link must be dropped.
    html = '<div class="result"><a class="result__snippet">orphan snippet</a></div>'
    parser = DuckDuckGoParser()
    parser.feed(html)
    assert parser.get_results() == []


# ── httpx stubs ──────────────────────────────────────────────────────────────
class _Resp:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    def json(self):
        return self._json


def _client_returning(resp, capture=None):
    """Build a fake httpx.AsyncClient context manager whose get/post return resp."""
    class _FakeClient:
        def __init__(self, *a, **k):
            pass

        @asynccontextmanager
        async def _cm(self):
            yield self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, **kwargs):
            if capture is not None:
                capture["get"] = (url, kwargs)
            return resp

        async def post(self, url, **kwargs):
            if capture is not None:
                capture["post"] = (url, kwargs)
            return resp

    return _FakeClient


# ── self-hosted search path ──────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_self_hosted_search_used_when_configured(monkeypatch):
    monkeypatch.setenv("ALADDINAI_SEARCH_URL", "https://search.local/")
    resp = _Resp(json_data={"results": [
        {"title": "T", "url": "https://x", "content": "snip"},
    ]})
    capture = {}
    with patch("httpx.AsyncClient", _client_returning(resp, capture)):
        out = await web_search(ToolContext(db=None, user_id=1), query="hello")
    assert out["results"] == [{"title": "T", "link": "https://x", "snippet": "snip"}]
    # trailing slash stripped, /search appended
    assert capture["get"][0] == "https://search.local/search"


# ── DuckDuckGo fallback path ─────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_falls_back_to_duckduckgo(monkeypatch):
    monkeypatch.delenv("ALADDINAI_SEARCH_URL", raising=False)
    monkeypatch.delenv("ALADDIN_SEARCH_URL", raising=False)
    html = ('<div class="result">'
            '<a class="result__a" href="https://ddg/a">DDG Title</a>'
            '<a class="result__snippet">ddg snippet</a></div>')
    with patch("httpx.AsyncClient", _client_returning(_Resp(text=html))):
        out = await web_search(ToolContext(db=None, user_id=1), query="q")
    assert out["results"][0]["title"] == "DDG Title"


@pytest.mark.asyncio
async def test_duckduckgo_captcha_returns_error(monkeypatch):
    monkeypatch.delenv("ALADDINAI_SEARCH_URL", raising=False)
    monkeypatch.delenv("ALADDIN_SEARCH_URL", raising=False)
    with patch("httpx.AsyncClient", _client_returning(_Resp(text="One last step - ddg-captcha"))):
        out = await web_search(ToolContext(db=None, user_id=1), query="q")
    assert out["results"] == []
    assert "error" in out


@pytest.mark.asyncio
async def test_duckduckgo_non_200_returns_error(monkeypatch):
    monkeypatch.delenv("ALADDINAI_SEARCH_URL", raising=False)
    monkeypatch.delenv("ALADDIN_SEARCH_URL", raising=False)
    with patch("httpx.AsyncClient", _client_returning(_Resp(status_code=503))):
        out = await web_search(ToolContext(db=None, user_id=1), query="q")
    assert out["results"] == []
    assert "503" in out["error"]
