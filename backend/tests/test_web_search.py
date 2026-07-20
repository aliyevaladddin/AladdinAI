# NOTICE: This file is protected under RCF-PL
"""Tests for the web_search tool and native meta-search service.

Covers tool registration, schema validity, the DuckDuckGoParser (pure),
and the meta_search service with mocked httpx — no real network calls.
"""
from unittest.mock import AsyncMock, patch

import pytest

import app.tools  # noqa: F401 — package import registers every tool as in prod
from app.tools.base import REGISTRY, ToolContext
from app.tools.web_search import DuckDuckGoParser, web_search


# ── registration + schema ────────────────────────────────────────────────────
def test_web_search_registered_via_package_import():
    assert "web_search" in REGISTRY


def test_web_search_schema_is_valid_function_schema():
    params = REGISTRY["web_search"].openai_schema()["function"]["parameters"]
    assert params["type"] == "object"
    assert "query" in params["properties"]
    assert params["required"] == ["query"]


# ── DuckDuckGoParser (pure, no network) ──────────────────────────────────────
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
    html = '<div class="result"><a class="result__snippet">orphan snippet</a></div>'
    parser = DuckDuckGoParser()
    parser.feed(html)
    assert parser.get_results() == []


# ── meta_search service (mocked) ─────────────────────────────────────────────
@pytest.mark.asyncio
async def test_meta_search_returns_merged_results():
    """meta_search returns results from all engines merged together."""
    from app.services.meta_search import meta_search

    ddg_result = {
        "Abstract": "",
        "AbstractText": "Python is a programming language.",
        "AbstractURL": "https://en.wikipedia.org/wiki/Python",
        "AbstractSource": "Wikipedia",
        "Heading": "Python",
        "Results": [],
        "RelatedTopics": [],
        "Definition": "",
        "DefinitionURL": "",
        "DefinitionSource": "",
    }
    wiki_result = {
        "query": {"search": [
            {"title": "Python", "snippet": "A programming language", "wordcount": 100},
        ]}
    }

    class _FakeResp:
        def __init__(self, data):
            self._data = data
            self.status_code = 200

        def json(self):
            return self._data

        def raise_for_status(self):
            pass

    async def fake_get(url, **kwargs):
        if "duckduckgo" in url:
            return _FakeResp(ddg_result)
        return _FakeResp(wiki_result)

    with patch("httpx.AsyncClient") as mock_cls:
        instance = AsyncMock()
        instance.get = AsyncMock(side_effect=fake_get)
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await meta_search("python", engines=["duckduckgo", "wikipedia"])

    assert isinstance(result["results"], list)
    assert result["query"] == "python"
    assert "errors" in result
    assert "by_source" in result


@pytest.mark.asyncio
async def test_meta_search_empty_query():
    from app.services.meta_search import meta_search
    result = await meta_search("  ")
    assert result["results"] == []
    assert result["errors"] == {}


@pytest.mark.asyncio
async def test_meta_search_arxiv_and_news():
    """meta_search parses ArXiv Atom XML and News RSS XML."""
    from app.services.meta_search import meta_search

    arxiv_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>http://arxiv.org/abs/2101.00001</id>
        <title>Quantum Computing Advances</title>
        <summary>A study on quantum algorithms.</summary>
      </entry>
    </feed>
    """

    news_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <item>
          <title>AI Revolution 2026</title>
          <link>https://news.example.com/ai</link>
          <pubDate>Mon, 20 Jul 2026 12:00:00 GMT</pubDate>
          <description>New breakthroughs in autonomous AI.</description>
        </item>
      </channel>
    </rss>
    """

    class _FakeTextResp:
        def __init__(self, text):
            self.text = text
            self.content = text.encode("utf-8")
            self.status_code = 200

        def raise_for_status(self):
            pass

    async def fake_get(url, **kwargs):
        if "arxiv" in url:
            return _FakeTextResp(arxiv_xml)
        return _FakeTextResp(news_xml)

    with patch("httpx.AsyncClient") as mock_cls:
        instance = AsyncMock()
        instance.get = AsyncMock(side_effect=fake_get)
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        res = await meta_search("quantum AI", engines=["arxiv", "news"])

    assert len(res["results"]) == 2
    sources = [r["source"] for r in res["results"]]
    assert "arxiv" in sources
    assert "news" in sources


# ── web_search tool delegates to meta_search ─────────────────────────────────
@pytest.mark.asyncio
async def test_web_search_tool_returns_results():
    """web_search tool correctly wraps meta_search output."""
    fake_meta = {
        "results": [
            {"title": "Test", "link": "https://test.com", "snippet": "A test", "source": "duckduckgo"},
        ],
        "by_source": {},
        "errors": {},
        "query": "test query",
    }
    with patch("app.services.meta_search.meta_search", AsyncMock(return_value=fake_meta)):
        out = await web_search(ToolContext(db=None, user_id=1), query="test query")

    assert out["query"] == "test query"
    assert len(out["results"]) == 1
    assert out["results"][0]["title"] == "Test"


@pytest.mark.asyncio
async def test_web_search_tool_surfaces_error_when_no_results():
    """web_search reports errors only when results list is empty."""
    fake_meta = {
        "results": [],
        "by_source": {},
        "errors": {"duckduckgo": "captcha", "wikipedia": "403"},
        "query": "q",
    }
    with patch("app.services.meta_search.meta_search", AsyncMock(return_value=fake_meta)):
        out = await web_search(ToolContext(db=None, user_id=1), query="q")

    assert out["results"] == []
    assert "error" in out


# ── synthesize endpoint ───────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_synthesize_endpoint_fallback_and_deep_scrape():
    """synthesize_search generates structured Markdown response with fallback when no LLM connected."""
    from app.routers.websearch import SynthesizeRequest, synthesize_search
    from app.models.user import User

    fake_meta = {
        "results": [
            {"title": "Python 3.12 Release", "link": "https://python.org", "snippet": "New features in Python 3.12", "source": "duckduckgo"},
        ],
        "by_source": {},
        "errors": {},
        "query": "python 3.12",
    }
    user = User(id=1, email="aladdin@example.com")
    db_mock = AsyncMock()

    with patch("app.routers.websearch.meta_search", AsyncMock(return_value=fake_meta)), \
         patch("app.routers.websearch.resolve_llm_provider", AsyncMock(side_effect=Exception("No LLM"))):
        
        req = SynthesizeRequest(query="python 3.12", deep=False, lang="en")
        res = await synthesize_search(req, user=user, db=db_mock)

    assert res.query == "python 3.12"
    assert "Python 3.12 Release" in res.synthesis
    assert len(res.sources) == 1
    assert res.scraped_urls == []

