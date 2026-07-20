# NOTICE: This file is protected under RCF-PL
"""Public-web search endpoint backing the dashboard Search page.

Thin HTTP layer over ``app.services.meta_search`` — the same native meta-search
the agent ``web_search`` tool uses.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.security import get_current_user
from app.services.browser import fetch_url_content
from app.services.llm_service import LLMError, chat_completion, resolve_llm_provider
from app.services.meta_search import DEFAULT_ENGINES, Engine, meta_search, _ALL_ENGINES

log = logging.getLogger(__name__)

router = APIRouter(prefix="/websearch", tags=["websearch"])


# [RCF:PROTECTED]
class WebSearchResult(BaseModel):
    title: str
    link: str
    snippet: str
    source: str


# [RCF:PROTECTED]
class WebSearchResponse(BaseModel):
    query: str
    results: list[WebSearchResult]
    by_source: dict[str, list[WebSearchResult]]
    errors: dict[str, str]
    total: int


class SynthesizeRequest(BaseModel):
    query: str
    deep: bool = False
    lang: str = "en"


class SynthesizeResponse(BaseModel):
    query: str
    synthesis: str
    sources: list[WebSearchResult]
    scraped_urls: list[str]
    model: str | None = None


# [RCF:PROTECTED]
@router.get("", response_model=WebSearchResponse)
# [RCF:PROTECTED]
async def web_search(
    q: str = Query(..., min_length=1, max_length=300),
    lang: str = Query("en", min_length=2, max_length=10),
    engines: str | None = Query(
        None,
        description="Comma-separated engine list (duckduckgo,wikipedia,arxiv,news). Defaults to all.",
    ),
    limit: int = Query(10, ge=1, le=25),
    user: User = Depends(get_current_user),
) -> WebSearchResponse:
    """Query public web sources and return merged + per-source results."""
    selected: tuple[Engine, ...] = DEFAULT_ENGINES
    if engines:
        parsed = tuple(
            e.strip() for e in engines.split(",") if e.strip() in _ALL_ENGINES
        )
        if parsed:
            selected = parsed  # type: ignore[assignment]

    data = await meta_search(q, engines=selected, lang=lang, limit=limit)
    results = data["results"]
    return WebSearchResponse(
        query=data["query"],
        results=results,          # type: ignore[arg-type]
        by_source=data["by_source"],  # type: ignore[arg-type]
        errors=data["errors"],    # type: ignore[arg-type]
        total=len(results),       # type: ignore[arg-type]
    )


@router.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize_search(
    body: SynthesizeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SynthesizeResponse:
    """Perplexity-style AI Synthesis endpoint.

    Gathers search results from meta_search, optionally deep-scrapes top 2-3 links
    with Chromium Headless Browser, and synthesizes a structured Markdown response
    with inline citations [1], [2].
    """
    query = body.query.strip()
    data = await meta_search(query, lang=body.lang, limit=10)
    raw_results = data["results"]
    sources = [
        WebSearchResult(
            title=r["title"],
            link=r["link"],
            snippet=r["snippet"],
            source=r["source"],
        )
        for r in raw_results
    ]

    scraped_data: dict[str, str] = {}
    scraped_urls: list[str] = []

    if body.deep and sources:
        candidate_urls = [s.link for s in sources if s.link.startswith("http")][:3]
        if candidate_urls:
            log.info("Deep AI Synthesis scraping URLs: %s", candidate_urls)
            fetch_tasks = [fetch_url_content(url, use_chromium=True) for url in candidate_urls]
            scraped_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
            for url, res in zip(candidate_urls, scraped_results):
                if isinstance(res, dict) and res.get("method") != "failed" and res.get("content"):
                    scraped_data[url] = res["content"][:2000]
                    scraped_urls.append(url)

    # Build prompt for LLM synthesis
    context_blocks = []
    for idx, s in enumerate(sources, start=1):
        block = f"[{idx}] Title: {s.title}\n    URL: {s.link}\n    Snippet: {s.snippet}"
        if s.link in scraped_data:
            block += f"\n    Deep Web Page Extract: {scraped_data[s.link]}"
        context_blocks.append(block)

    sources_str = "\n\n".join(context_blocks)
    sys_prompt = (
        "You are an AI Search Synthesizer (Perplexity-style).\n"
        "Synthesize a comprehensive, well-structured, objective answer to the user's query based ONLY on the provided search results and web extracts.\n"
        "Rules:\n"
        "1. Include inline numbered citations like [1], [2] matching the source numbers.\n"
        "2. Structure your response with clear Markdown headings, bullet points, and key takeaways.\n"
        "3. Respond in the requested language (language code: " + body.lang + ").\n"
        "4. Be direct, authoritative, and informative."
    )
    user_prompt = f"Query: {query}\n\nSearch Results:\n{sources_str}"

    model_name: str | None = None
    try:
        provider = await resolve_llm_provider(db, user.id)
        model_name = provider.default_model or "default"
        resp = await chat_completion(
            provider,
            model_name,
            [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=1500,
        )
        synthesis_text = resp.get("content") or "Unable to synthesize an answer."
    except (LLMError, Exception) as e:
        log.warning("AI Synthesis LLM call failed, generating fallback summary: %s", e)
        # Clean fallback summary if no LLM provider is connected
        bullet_items = "\n".join(f"- **[{idx}] {s.title}**: {s.snippet}" for idx, s in enumerate(sources[:5], start=1))
        synthesis_text = (
            f"### Key Information for \"{query}\"\n\n"
            f"{bullet_items}\n\n"
            "*(Note: Connect an LLM provider in Settings for AI-synthesized answers with full analytical narrative.)*"
        )

    return SynthesizeResponse(
        query=query,
        synthesis=synthesis_text,
        sources=sources,
        scraped_urls=scraped_urls,
        model=model_name,
    )

