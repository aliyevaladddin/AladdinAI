# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
from __future__ import annotations

import os
import logging
from typing import Any
from html.parser import HTMLParser
import httpx

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
    
    Queries your own self-hosted search service (e.g. AladdinAI Search)
    if ALADDINAI_SEARCH_URL or ALADDIN_SEARCH_URL is configured, otherwise falls back to DuckDuckGo HTML scraping.
    """
    search_url = os.getenv("ALADDINAI_SEARCH_URL") or os.getenv("ALADDIN_SEARCH_URL")
    
    # 1. Try custom self-hosted search service if configured
    if search_url:
        # Strip trailing slash if present
        search_url = search_url.rstrip("/")
        logger.info(f"Performing web search using AladdinAI Search at: {search_url}")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {}
                api_key = os.getenv("ALADDINAI_SEARCH_API_KEY")
                if api_key:
                    headers["X-API-KEY"] = api_key

                resp = await client.get(
                    f"{search_url}/search",
                    params={"q": query, "format": "json"},
                    headers=headers
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for item in data.get("results", []):
                        results.append({
                            "title": item.get("title", ""),
                            "link": item.get("url", ""),
                            "snippet": item.get("content", "")
                        })
                    return {"query": query, "results": results}
                else:
                    logger.warning(f"Search service returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"Error performing search with custom search service: {e}")

    # 2. Fallback to DuckDuckGo HTML Scraper (used in tests and local-dev)
    logger.info("Performing web search using DuckDuckGo HTML scraping.")
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query},
                headers=headers
            )
            if resp.status_code != 200:
                logger.warning(f"DuckDuckGo search failed with status {resp.status_code}")
                return {"query": query, "results": [], "error": f"Search engine returned status {resp.status_code}"}
                
            parser = DuckDuckGoParser()
            parser.feed(resp.text)
            results = parser.get_results()
            
            if not results:
                if "ddg-captcha" in resp.text or "Turnstile" in resp.text or "One last step" in resp.text:
                    err_msg = "Search failed because the search engine blocked the request (Captcha/Turnstile challenge)."
                    logger.warning(err_msg)
                    return {"query": query, "results": [], "error": err_msg}
            
            return {"query": query, "results": results}
            
    except Exception as e:
        logger.error(f"Error performing DuckDuckGo scraping: {e}")
        return {"query": query, "results": [], "error": str(e)}
