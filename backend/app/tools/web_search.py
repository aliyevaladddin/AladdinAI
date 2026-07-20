# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
from __future__ import annotations

import logging
from typing import Any
from html.parser import HTMLParser

from app.tools.base import ToolContext, tool

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# [RCF:PROTECTED]
class DuckDuckGoParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results = []
        self.current_result = None
        self.in_title = False
        self.in_snippet = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        cls = attrs_dict.get("class", "")
        
        # Look for result container div
        if tag == "div" and "result" in cls.split():
            if self.current_result:
                self.results.append(self.current_result)
            self.current_result = {"title": "", "link": "", "snippet": ""}
            
        if self.current_result:
            if tag == "a" and "result__a" in cls.split():
                self.in_title = True
                self.current_result["link"] = attrs_dict.get("href", "")
            elif tag == "a" and "result__snippet" in cls.split():
                self.in_snippet = True
                if not self.current_result.get("link"):
                    self.current_result["link"] = attrs_dict.get("href", "")

    def handle_endtag(self, tag):
        if tag == "a":
            self.in_title = False
            self.in_snippet = False

    def handle_data(self, data):
        if self.current_result:
            if self.in_title:
                self.current_result["title"] += data
            elif self.in_snippet:
                self.current_result["snippet"] += data

    def get_results(self) -> list[dict[str, str]]:
        if self.current_result:
            self.results.append(self.current_result)
            self.current_result = None
        
        cleaned = []
        for r in self.results:
            title = r.get("title", "").strip()
            link = r.get("link", "").strip()
            snippet = r.get("snippet", "").strip()
            if title and link:
                cleaned.append({
                    "title": title,
                    "link": link,
                    "snippet": snippet
                })
        return cleaned


# [RCF:PROTECTED]
@tool(
    name="web_search",
    description=(
        "Search the web for information using a search engine. "
        "Returns a list of search results containing titles, links, and snippets."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query to lookup."}
        },
        "required": ["query"],
    }
)
async def web_search(ctx: ToolContext, query: str) -> dict[str, Any]:
    """Search the web for the given query.

    Uses the native meta-search service (app.services.meta_search): DuckDuckGo
    and Wikipedia queried directly and in parallel. No self-hosted engine and
    no external gateway.
    """
    # Imported lazily to avoid a circular import: meta_search imports the
    # DuckDuckGoParser defined above in this module.
    from app.services.meta_search import meta_search

    logger.info("Performing web search via native meta-search: %s", query)
    try:
        data = await meta_search(query)
        results = [
            {"title": r["title"], "link": r["link"], "snippet": r["snippet"]}
            for r in data["results"]
        ]
        out: dict[str, Any] = {"query": query, "results": results}
        # Surface an error only when every source failed and nothing came back.
        if not results and data["errors"]:
            out["error"] = "; ".join(
                f"{eng}: {msg}" for eng, msg in data["errors"].items()
            )
        return out
    except Exception as e:  # pragma: no cover - defensive
        logger.error("Error performing web search: %s", e)
        return {"query": query, "results": [], "error": str(e)}
