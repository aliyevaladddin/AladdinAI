// NOTICE: This file is protected under RCF-PL
# ADR-0010: Native Agent Meta-Search Engine & Universal Tool Discovery

**Status**: Accepted

**Date**: 2026-07-20

**Deciders**: AladdinAI core team

**Tags**: backend, tools, agents, search, architecture

## Context

Agents in AladdinAI require real-time web research capabilities to solve user tasks requiring up-to-date knowledge. Previously, web search relied on external third-party proxies or heavy bundled services (such as SearXNG), which introduced deployment overhead, strict rate limiting, or potential single points of failure. Additionally, the tool capability whitelist in `capabilities.py` was overly restrictive, preventing modern instruction-tuned model families (e.g., Qwen, DeepSeek, Claude, Llama 3.1+, Dracarys) from triggering `web_search`.

## Decision

We introduced a native, asynchronous meta-search engine directly into the backend core (`app/services/meta_search.py`) along with an expanded universal model capability heuristic in `app/tools/capabilities.py`.

### Architecture Highlights
1. **Parallel Multi-Source Orchestrator**: The native meta-search engine queries **DuckDuckGo**, **Wikipedia**, **ArXiv**, and **Google News RSS** in parallel using `httpx.AsyncClient` with non-blocking concurrency (`asyncio.gather`).
2. **DuckDuckGo Dual-Tier & HTML Fallback**: DuckDuckGo uses Instant Answer API zero-click definitions first, automatically falling back to DDG HTML scraping via `DuckDuckGoParser` if zero answers are returned.
3. **Out-of-the-Box Zero-Key Design**: Completely free academic (ArXiv) and news (Google News RSS) integration out of the box with zero external API keys or rate-limited third-party services (Brave Search API removed).
4. **Universal Tool Capability Heuristic**: Updated `model_supports_tools` to dynamically match modern LLM model prefixes, ensuring agents configured with modern LLM providers can autonomously invoke `web_search`.
5. **Dashboard Web Search API & Interactive UI**: Exposed `/api/websearch` REST endpoint backing the interactive frontend Search view in `frontend/src/app/(dashboard)/dashboard/search/page.tsx` with dedicated source tabs (All, Web, Wikipedia, News, Research) and color-coded badges.

## Consequences

### Positive
- Zero external search gateway dependency required for base agent operation.
- Immediate response latency improvement due to parallel multi-source querying across web, encyclopedic, academic, and news sources.
- Autonomous web search enabled across all configured agent model families.
- 100% out-of-the-box developer experience with zero required API keys or quota limits.

### Negative
- Direct HTML scraping fallback for DuckDuckGo depends on upstream DOM structure stability.

### Neutral
- Academic research (ArXiv Atom XML) and news items (Google News RSS) are formatted cleanly with dates and snippets into a unified `SearchResult` schema.

## Alternatives Considered

### Alternative 1: Bundled SearXNG Docker Service
- **Description**: Running SearXNG as a sidecar container in `docker-compose.yml`.
- **Pros**: Aggregates many search engines automatically.
- **Cons**: High container memory footprint, default JSON API disabled, potential 403 Forbidden issues, extra configuration friction for `npx aladdin-ai init`.
- **Why not chosen**: Native backend meta-search provides superior speed, zero extra container overhead, and simpler setup.

## Implementation Notes

- Service implementation: `backend/app/services/meta_search.py`
- Tool wrapper: `backend/app/tools/web_search.py`
- Capability discovery: `backend/app/tools/capabilities.py`
- REST endpoint: `backend/app/routers/websearch.py`
- Unit tests: `backend/tests/test_web_search.py` (100% test coverage)

## References

- ADR-0006: Open-Core Edition Boundary
- ADR-0009: Golden Set + Evaluation Harness
