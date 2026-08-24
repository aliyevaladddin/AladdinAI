// NOTICE: This file is protected under RCF-PL
# Web Search (Native Meta-Search)

AladdinAI's `web_search` tool and the `/api/websearch` route both run on a
**native meta-search** service: no external gateway, no self-hosted engine,
no API keys.

Design rationale lives in
[`docs/adr/0010-native-agent-meta-search.md`](../adr/0010-native-agent-meta-search.md).

---

## Engines

All four are free, zero-key sources:

| Engine | Source | Best for |
|---|---|---|
| `duckduckgo` | DDG Instant Answer API + HTML fallback | General web results |
| `wikipedia` | Wikipedia public search API | Encyclopedic facts |
| `arxiv` | arXiv Atom API | Academic papers |
| `news` | Google News RSS | Fresh events |

Wikipedia calls carry a descriptive User-Agent per Wikimedia API etiquette.

---

## How it works

```
meta_search(query, engines, lang, limit)
        │
        ├── asyncio.gather over selected engines   ← total latency = slowest source
        ├── _with_retry (3 attempts, backoff)       ← only transient httpx errors
        └── merge → { query, results, by_source, errors }
```

Key properties:

- **Independent failure** — one engine timing out never aborts the others;
  its slice is empty and the failure is reported in `errors`.
- **Concurrent** — sources run in parallel via `asyncio.gather`.
- **Retried** — `ConnectError`, timeouts and protocol errors are retried 3×
  with increasing delay.
- **Typed** — returns a `MetaSearchResponse(TypedDict)` with
  `results: list[SearchResult]`, not a loose dict.

---

## HTTP API

### `GET /api/websearch?q=...&engines=duckduckgo,wikipedia&lang=en&limit=10`

Returns a `WebSearchResponse`:

```json
{
  "query": "python asyncio",
  "results": [
    {"title": "...", "link": "https://...", "snippet": "...", "source": "duckduckgo"}
  ],
  "by_source": { "duckduckgo": [ ... ], "wikipedia": [ ... ] },
  "errors": {},
  "total": 1
}
```

### `POST /api/websearch/synthesize`

Perplexity-style synthesis: gathers results, deep-scrapes the top links with
a headless browser when available, and returns structured Markdown with
inline citations (`[1]`, `[2]`).

---

## Agent tool

Agents call the registered `web_search` tool; it wraps `meta_search` and
adds an `error` key **only when every source failed** — partial failures are
surfaced as normal (possibly partial) results so agent loops don't stall.

```python
from app.tools.web_search import web_search  # auto-registered via app.tools
```

---

## Testing

Tests mock `httpx` entirely — no real network:

- [`backend/tests/test_web_search.py`](../../backend/tests/test_web_search.py) — parser, retry, service
- [`backend/tests/test_websearch_routes.py`](../../backend/tests/test_websearch_routes.py) — HTTP endpoints

---

## See also

- [`docs/guides/TOOL_DEVELOPMENT.md`](TOOL_DEVELOPMENT.md) — how tools like this are registered
