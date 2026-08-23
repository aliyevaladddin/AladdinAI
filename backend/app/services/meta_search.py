# NOTICE: This file is protected under RCF-PL
"""Native meta-search: no external gateway, no self-hosted engine, no API keys.

Engines (all free, zero-key):
  - duckduckgo  — DDG Instant Answer API (zero-click + topics), HTML fallback.
  - wikipedia   — Wikipedia public search API.
  - arxiv       — arXiv Atom API for academic papers.
  - news        — Google News RSS.

Sources run concurrently via ``asyncio.gather`` so the total latency is that
of the slowest source, not their sum. Each source fails independently: if one
raises or times out its slice is simply empty, and the others still return.

The backend web_search tool and the /api/websearch route both call
``meta_search`` — this module is the single source of truth for web results.
"""

from __future__ import annotations

import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from typing import Literal, TypedDict

import httpx

from app.tools.web_search import USER_AGENT

# Wikipedia Wikimedia API policy requires a descriptive User-Agent with contact.
# https://www.mediawiki.org/wiki/API:Etiquette
_WIKI_UA = "AladdinAI/2.0 (https://github.com/aliyevaladddin/AladdinAI; aladdin@aliyev.site) httpx/0.27"

logger = logging.getLogger(__name__)

Engine = Literal["duckduckgo", "wikipedia", "arxiv", "news"]
DEFAULT_ENGINES: tuple[Engine, ...] = ("duckduckgo", "wikipedia", "news", "arxiv")

_TIMEOUT = httpx.Timeout(15.0)
_RETRY_ATTEMPTS = 3
_RETRY_DELAY = 0.8  # seconds between retries

# Exceptions that indicate a transient network/DNS issue worth retrying.
_RETRYABLE = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.RemoteProtocolError,
)


async def _with_retry(coro_factory, attempts: int = _RETRY_ATTEMPTS):
    """Run coro_factory() up to `attempts` times on transient network errors."""
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            return await coro_factory()
        except _RETRYABLE as exc:
            last_exc = exc
            if attempt < attempts - 1:
                await asyncio.sleep(_RETRY_DELAY * (attempt + 1))
                logger.debug("meta_search retry %d/%d after: %s", attempt + 1, attempts, exc)
    assert last_exc is not None
    raise last_exc

# ── HTML tag stripper ────────────────────────────────────────────────────────
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _TAG_RE.sub("", text).strip()


# [RCF:PROTECTED]
class SearchResult(TypedDict):
    title: str
    link: str
    snippet: str
    source: str


class MetaSearchResponse(TypedDict, total=False):
    """Return type for :func:`meta_search`.

    Callers always receive all four keys; ``total=False`` only keeps the
    TypedDict lightweight — every key is populated by the orchestrator.
    """
    query: str
    results: list[SearchResult]
    by_source: dict[str, list[SearchResult]]
    errors: dict[str, str]


# ── DuckDuckGo Instant Answer API ────────────────────────────────────────────
# [RCF:PROTECTED]
async def _search_duckduckgo(
    client: httpx.AsyncClient, query: str, limit: int
) -> list[SearchResult]:
    """DuckDuckGo web search — HTML scrape (primary) + Instant Answer (bonus).

    The HTML endpoint returns real web search results. The Instant Answer API
    only provides definitions and related topics — useful as enrichment but
    insufficient on its own.
    """
    results: list[SearchResult] = []

    # 1. Primary: HTML search — full web results from html.duckduckgo.com
    try:
        html_resp = await client.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers={"User-Agent": USER_AGENT},
            timeout=10.0,
        )
        if html_resp.status_code == 200:
            from app.tools.web_search import DuckDuckGoParser
            parser = DuckDuckGoParser()
            parser.feed(html_resp.text)
            for item in parser.get_results()[:limit]:
                results.append(SearchResult(
                    title=item["title"],
                    link=item["link"],
                    snippet=(item.get("snippet") or "")[:300],
                    source="duckduckgo",
                ))
    except Exception as exc:
        logger.debug("DuckDuckGo HTML search failed: %s", exc)

    # 2. Bonus: Instant Answer API — definitions, abstracts, related topics
    #    Add only if they aren't duplicates of what HTML search already found.
    existing_links = {r.link for r in results}
    try:
        resp = await client.get(
            "https://api.duckduckgo.com/",
            params={
                "q": query,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1",
                "no_redirect": "1",
            },
            headers={"User-Agent": USER_AGENT},
            timeout=5.0,
        )
        resp.raise_for_status()
        data = resp.json()

        # Abstract
        abstract_text = (data.get("AbstractText") or "").strip()
        abstract_url = (data.get("AbstractURL") or "").strip()
        heading = (data.get("Heading") or query).strip()
        if abstract_text and abstract_url and abstract_url not in existing_links:
            results.insert(0, SearchResult(
                title=heading,
                link=abstract_url,
                snippet=abstract_text[:300],
                source="duckduckgo",
            ))

        # Related topics (only unique links)
        for topic in data.get("RelatedTopics", []):
            if len(results) >= limit:
                break
            topics = topic.get("Topics", [topic])
            for sub in topics:
                if len(results) >= limit:
                    break
                url = (sub.get("FirstURL") or "").strip()
                text = _strip_html(sub.get("Text") or "")
                if url and text and url not in existing_links:
                    title = text.split(" - ")[0][:100] if " - " in text else text[:80]
                    results.append(SearchResult(
                        title=title,
                        link=url,
                        snippet=text[:300],
                        source="duckduckgo",
                    ))
                    existing_links.add(url)
    except Exception as exc:
        logger.debug("DuckDuckGo Instant Answer API failed: %s", exc)

    return results[:limit]


# ── Wikipedia ────────────────────────────────────────────────────────────────
# [RCF:PROTECTED]
async def _search_wikipedia(
    client: httpx.AsyncClient, query: str, limit: int, lang: str
) -> list[SearchResult]:
    """Encyclopedic summaries via the Wikipedia public search API."""
    resp = await client.get(
        f"https://{lang}.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
        },
        headers={"User-Agent": _WIKI_UA},
    )
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        return []
    query_data = data.get("query") or {}
    hits = query_data.get("search") or []
    results: list[SearchResult] = []
    for hit in hits:
        if isinstance(hit, dict):
            title = hit.get("title", "")
            snippet = _strip_html(hit.get("snippet", ""))
            slug = title.replace(" ", "_")
            results.append(SearchResult(
                title=title,
                link=f"https://{lang}.wikipedia.org/wiki/{slug}",
                snippet=snippet,
                source="wikipedia",
            ))
    return results


# ── ArXiv API ────────────────────────────────────────────────────────────────
# [RCF:PROTECTED]
async def _search_arxiv(
    client: httpx.AsyncClient, query: str, limit: int
) -> list[SearchResult]:
    """ArXiv API — free public search for academic papers and research."""
    resp = await client.get(
        "https://export.arxiv.org/api/query",
        params={
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": limit,
        },
        headers={"User-Agent": USER_AGENT},
    )
    resp.raise_for_status()

    results: list[SearchResult] = []
    try:
        root = ET.fromstring(resp.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns)[:limit]:
            title_elem = entry.find("atom:title", ns)
            id_elem = entry.find("atom:id", ns)
            summary_elem = entry.find("atom:summary", ns)

            raw_title = title_elem.text if title_elem is not None and title_elem.text else ""
            title = _strip_html(raw_title).replace("\n", " ").strip()
            link = id_elem.text.strip() if id_elem is not None and id_elem.text else ""
            raw_summary = summary_elem.text if summary_elem is not None and summary_elem.text else ""
            snippet = _strip_html(raw_summary).replace("\n", " ").strip()

            if title and link:
                results.append(SearchResult(
                    title=title,
                    link=link,
                    snippet=snippet[:350],
                    source="arxiv",
                ))
    except Exception as exc:
        logger.warning("Failed to parse ArXiv XML response: %s", exc)

    return results


# ── Google News RSS ──────────────────────────────────────────────────────────
# [RCF:PROTECTED]
async def _search_news(
    client: httpx.AsyncClient, query: str, limit: int, lang: str
) -> list[SearchResult]:
    """Google News RSS — free public news aggregator."""
    gl = "US" if lang.lower() == "en" else lang.upper()
    resp = await client.get(
        "https://news.google.com/rss/search",
        params={
            "q": query,
            "hl": lang,
            "gl": gl,
            "ceid": f"{gl}:{lang}",
        },
        headers={"User-Agent": USER_AGENT},
    )
    resp.raise_for_status()

    results: list[SearchResult] = []
    try:
        root = ET.fromstring(resp.content)
        channel = root.find("channel")
        if channel is not None:
            for item in channel.findall("item")[:limit]:
                title_elem = item.find("title")
                link_elem = item.find("link")
                pub_date_elem = item.find("pubDate")
                desc_elem = item.find("description")

                raw_title = title_elem.text if title_elem is not None and title_elem.text else ""
                title = _strip_html(raw_title).strip()
                link = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
                pub_date = pub_date_elem.text.strip() if pub_date_elem is not None and pub_date_elem.text else ""
                raw_desc = desc_elem.text if desc_elem is not None and desc_elem.text else ""
                snippet = _strip_html(raw_desc).strip()
                if pub_date:
                    snippet = f"[{pub_date}] {snippet}"

                if title and link:
                    results.append(SearchResult(
                        title=title,
                        link=link,
                        snippet=snippet[:300],
                        source="news",
                    ))
    except Exception as exc:
        logger.warning("Failed to parse News RSS response: %s", exc)

    return results


# ── Orchestrator ─────────────────────────────────────────────────────────────
_ALL_ENGINES: tuple[Engine, ...] = ("duckduckgo", "wikipedia", "arxiv", "news")


# [RCF:PROTECTED]
async def meta_search(
    query: str,
    *,
    engines: tuple[Engine, ...] | list[Engine] = DEFAULT_ENGINES,
    lang: str = "en",
    limit: int = 10,
) -> MetaSearchResponse:
    """Run the requested engines concurrently and merge their results.

    Returns ``{"query", "results", "by_source", "errors"}``. A failing engine
    contributes an entry to ``errors`` but never aborts the others.
    """
    query = (query or "").strip()
    if not query:
        return {"query": query, "results": [], "by_source": {}, "errors": {}}

    wanted = [e for e in engines if e in _ALL_ENGINES] or list(DEFAULT_ENGINES)

    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        tasks = []
        for engine in wanted:
            if engine == "duckduckgo":
                tasks.append(_with_retry(lambda e=engine, c=client: _search_duckduckgo(c, query, limit)))
            elif engine == "wikipedia":
                tasks.append(_with_retry(lambda e=engine, c=client: _search_wikipedia(c, query, limit, lang)))
            elif engine == "arxiv":
                tasks.append(_with_retry(lambda e=engine, c=client: _search_arxiv(c, query, limit)))
            elif engine == "news":
                tasks.append(_with_retry(lambda e=engine, c=client: _search_news(c, query, limit, lang)))
        settled = await asyncio.gather(*tasks, return_exceptions=True)

    merged: list[SearchResult] = []
    by_source: dict[str, list[SearchResult]] = {}
    errors: dict[str, str] = {}
    for engine, outcome in zip(wanted, settled):
        if isinstance(outcome, Exception):
            errors[engine] = str(outcome)
            by_source[engine] = []
            continue
        assert isinstance(outcome, list)
        by_source[engine] = outcome
        merged.extend(outcome)

    # Log source issues gracefully: if we got results overall, individual source fails are non-fatal
    for engine, err in errors.items():
        if merged:
            logger.info("meta_search: source %r failed (non-fatal, got %d merged results): %s", engine, len(merged), err)
        else:
            logger.warning("meta_search: source %r failed: %s", engine, err)

    return {
        "query": query,
        "results": merged,
        "by_source": by_source,
        "errors": errors,
    }
