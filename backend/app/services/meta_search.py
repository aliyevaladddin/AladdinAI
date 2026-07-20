# NOTICE: This file is protected under RCF-PL
"""Native meta-search: no external gateway, no self-hosted engine.

Engines:
  - duckduckgo  — DDG Instant Answer API (free, no key, zero-click + topics).
  - brave       — Brave Search API (free 2000 req/month, needs BRAVE_API_KEY).
  - wikipedia   — Wikipedia public search API (always free, no key).

Sources run concurrently via ``asyncio.gather`` so the total latency is that
of the slowest source, not their sum. Each source fails independently: if one
raises or times out its slice is simply empty, and the others still return.

The backend web_search tool and the /api/websearch route both call
``meta_search`` — this module is the single source of truth for web results.

Environment variables:
  BRAVE_API_KEY   — optional. Enables the ``brave`` engine. Get a free key at
                    https://api.search.brave.com/register (2 000 req/month free).
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Literal, TypedDict

import httpx

from app.tools.web_search import USER_AGENT

# Wikipedia Wikimedia API policy requires a descriptive User-Agent with contact.
# https://www.mediawiki.org/wiki/API:Etiquette
_WIKI_UA = "AladdinAI/2.0 (https://github.com/aliyevaladddin/AladdinAI; aladdin@aliyev.site) httpx/0.27"

logger = logging.getLogger(__name__)

Engine = Literal["duckduckgo", "brave", "wikipedia"]
DEFAULT_ENGINES: tuple[Engine, ...] = ("duckduckgo", "wikipedia")

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
    raise last_exc  # type: ignore[misc]

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


# ── DuckDuckGo Instant Answer API ────────────────────────────────────────────
# [RCF:PROTECTED]
async def _search_duckduckgo(
    client: httpx.AsyncClient, query: str, limit: int
) -> list[SearchResult]:
    """DDG Instant Answer API — free, no key required.

    Returns zero-click answers, definitions and related topics.
    Less comprehensive than full web-search but always available without
    bot-detection issues.
    """
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
    )
    resp.raise_for_status()
    data = resp.json()

    results: list[SearchResult] = []

    # 1. Direct answer / abstract
    abstract_text = (data.get("AbstractText") or "").strip()
    abstract_url = (data.get("AbstractURL") or "").strip()
    abstract_src = (data.get("AbstractSource") or "DuckDuckGo").strip()
    heading = (data.get("Heading") or query).strip()
    if abstract_text and abstract_url:
        results.append(SearchResult(
            title=heading,
            link=abstract_url,
            snippet=abstract_text[:300],
            source="duckduckgo",
        ))

    # 2. Direct results (e.g. official website)
    for r in data.get("Results", [])[:2]:
        url = (r.get("FirstURL") or "").strip()
        text = _strip_html(r.get("Text") or "")
        if url and text:
            results.append(SearchResult(
                title=text[:80],
                link=url,
                snippet=text,
                source="duckduckgo",
            ))

    # 3. Related topics (richest source of results)
    for topic in data.get("RelatedTopics", []):
        if len(results) >= limit:
            break
        # Topics can be nested groups
        if "Topics" in topic:
            for sub in topic["Topics"]:
                if len(results) >= limit:
                    break
                url = (sub.get("FirstURL") or "").strip()
                text = _strip_html(sub.get("Text") or "")
                if url and text:
                    title = text.split(" - ")[0][:100] if " - " in text else text[:80]
                    snippet = text
                    results.append(SearchResult(
                        title=title,
                        link=url,
                        snippet=snippet[:300],
                        source="duckduckgo",
                    ))
        else:
            url = (topic.get("FirstURL") or "").strip()
            text = _strip_html(topic.get("Text") or "")
            if url and text:
                title = text.split(" - ")[0][:100] if " - " in text else text[:80]
                results.append(SearchResult(
                    title=title,
                    link=url,
                    snippet=text[:300],
                    source="duckduckgo",
                ))

    # 4. Definition
    definition = (data.get("Definition") or "").strip()
    definition_url = (data.get("DefinitionURL") or "").strip()
    definition_src = (data.get("DefinitionSource") or "").strip()
    if definition and definition_url and len(results) < limit:
        results.append(SearchResult(
            title=f"Definition ({definition_src})" if definition_src else "Definition",
            link=definition_url,
            snippet=definition[:300],
            source="duckduckgo",
        ))

    return results[:limit]


# ── Brave Search API ─────────────────────────────────────────────────────────
# [RCF:PROTECTED]
async def _search_brave(
    client: httpx.AsyncClient, query: str, limit: int, lang: str
) -> list[SearchResult]:
    """Brave Search API — 2 000 free requests/month.

    Requires BRAVE_API_KEY env var. Register at https://api.search.brave.com/register
    """
    api_key = os.getenv("BRAVE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("BRAVE_API_KEY not set — skipping Brave engine")

    resp = await client.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query, "count": min(limit, 20), "search_lang": lang},
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key,
        },
    )
    resp.raise_for_status()
    data = resp.json()

    results: list[SearchResult] = []
    for item in data.get("web", {}).get("results", [])[:limit]:
        results.append(SearchResult(
            title=item.get("title", ""),
            link=item.get("url", ""),
            snippet=item.get("description", ""),
            source="brave",
        ))
    return results


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
    hits = data.get("query", {}).get("search", [])
    results: list[SearchResult] = []
    for hit in hits:
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


# ── Orchestrator ─────────────────────────────────────────────────────────────
_ALL_ENGINES: tuple[Engine, ...] = ("duckduckgo", "brave", "wikipedia")


# [RCF:PROTECTED]
async def meta_search(
    query: str,
    *,
    engines: tuple[Engine, ...] | list[Engine] = DEFAULT_ENGINES,
    lang: str = "en",
    limit: int = 10,
) -> dict[str, object]:
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
            elif engine == "brave":
                tasks.append(_with_retry(lambda e=engine, c=client: _search_brave(c, query, limit, lang)))
            elif engine == "wikipedia":
                tasks.append(_with_retry(lambda e=engine, c=client: _search_wikipedia(c, query, limit, lang)))
        settled = await asyncio.gather(*tasks, return_exceptions=True)

    merged: list[SearchResult] = []
    by_source: dict[str, list[SearchResult]] = {}
    errors: dict[str, str] = {}
    for engine, outcome in zip(wanted, settled):
        if isinstance(outcome, Exception):
            errors[engine] = str(outcome)
            by_source[engine] = []
            continue
        by_source[engine] = outcome  # type: ignore[assignment]
        merged.extend(outcome)  # type: ignore[arg-type]

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
