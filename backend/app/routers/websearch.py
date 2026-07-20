# NOTICE: This file is protected under RCF-PL
"""Public-web search endpoint backing the dashboard Search page.

Thin HTTP layer over ``app.services.meta_search`` — the same native meta-search
the agent ``web_search`` tool uses.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.models.user import User
from app.security import get_current_user
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


# [RCF:PROTECTED]
@router.get("", response_model=WebSearchResponse)
# [RCF:PROTECTED]
async def web_search(
    q: str = Query(..., min_length=1, max_length=300),
    lang: str = Query("en", min_length=2, max_length=10),
    engines: str | None = Query(
        None,
        description="Comma-separated engine list (duckduckgo,wikipedia). Defaults to all.",
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
