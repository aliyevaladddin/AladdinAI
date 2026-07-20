# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
from __future__ import annotations

import logging
import re
from html.parser import HTMLParser
from typing import Any

import httpx

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class HTMLTextExtractor(HTMLParser):
    """Clean text extractor stripping script, style, and navigation noise."""

    def __init__(self) -> None:
        super().__init__()
        self._ignore = False
        self._chunks: list[str] = []
        self._title = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in ("script", "style", "noscript", "svg", "header", "footer", "nav"):
            self._ignore = True
        elif tag.lower() == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in ("script", "style", "noscript", "svg", "header", "footer", "nav"):
            self._ignore = False
        elif tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title += data
        elif not self._ignore:
            text = data.strip()
            if text:
                self._chunks.append(text)

    def get_text(self) -> str:
        text = "\n".join(self._chunks)
        # Collapse multiple newlines
        return re.sub(r"\n{3,}", "\n\n", text)

    def get_title(self) -> str:
        return self._title.strip()


async def fetch_url_content(
    url: str,
    timeout: int = 15,
    use_chromium: bool = True,
    max_length: int = 12000,
) -> dict[str, Any]:
    """Fetch URL content via Playwright Chromium (if available) or HTTPX fallback.

    Returns dict with keys: url, title, content, method ('chromium' or 'httpx'), status.
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Try Chromium via Playwright first if enabled
    if use_chromium:
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
                )
                context = await browser.new_context(
                    user_agent=USER_AGENT,
                    viewport={"width": 1280, "height": 800},
                )
                page = await context.new_page()
                try:
                    resp = await page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
                    title = await page.title()
                    # Extract inner text of body or main element
                    content = await page.evaluate(
                        """() => {
                            const main = document.querySelector('article') || document.querySelector('main') || document.body;
                            return main ? main.innerText : document.body.innerText;
                        }"""
                    )
                    status = resp.status if resp else 200
                    await browser.close()

                    clean_content = re.sub(r"\n{3,}", "\n\n", content.strip())
                    if len(clean_content) > max_length:
                        clean_content = clean_content[:max_length] + "\n\n... [Content truncated]"

                    return {
                        "url": url,
                        "title": title or "No Title",
                        "content": clean_content,
                        "method": "chromium",
                        "status": status,
                    }
                except Exception as exc:
                    await browser.close()
                    logger.warning("Chromium fetch failed for %s, falling back to HTTPX: %s", url, exc)
        except Exception as exc:
            logger.info("Playwright unavailable or initialization failed: %s", exc)

    # Fallback to HTTPX + HTML text extraction
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            parser = HTMLTextExtractor()
            parser.feed(resp.text)
            content = parser.get_text()
            title = parser.get_title() or url

            if len(content) > max_length:
                content = content[:max_length] + "\n\n... [Content truncated]"

            return {
                "url": url,
                "title": title,
                "content": content,
                "method": "httpx",
                "status": resp.status_code,
            }
    except Exception as exc:
        logger.error("HTTPX fetch failed for %s: %s", url, exc)
        return {
            "url": url,
            "title": "Error",
            "content": f"Failed to fetch content from {url}: {exc}",
            "method": "failed",
            "status": 500,
        }
