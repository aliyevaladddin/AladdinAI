# NOTICE: This file is protected under RCF-PL
"""PDF text extraction that never blocks the event loop.

pypdf is synchronous pure Python, and hostile or merely heavy PDFs can keep it
busy for a long time (CVE-2026-119203/119204/119205 are all parser resource
exhaustion). Calling it inline from an `async def` stalls the whole uvicorn
worker, so every request in the process waits, not just the upload that caused
it. Parsing therefore runs in a worker thread.
"""
from __future__ import annotations

import asyncio
import io


def _extract_pages_sync(data: bytes) -> list[str]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return [page.extract_text() or "" for page in reader.pages]


async def extract_pdf_pages(data: bytes) -> list[str]:
    """Return text per page ("" for pages without an extractable text layer).

    Raises whatever pypdf raises; callers decide how to degrade. Only the
    parsing is offloaded — the caller stays responsible for how pages are
    joined, so existing output formatting is unchanged.
    """
    return await asyncio.to_thread(_extract_pages_sync, data)
