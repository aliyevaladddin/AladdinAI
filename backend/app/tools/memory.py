"""Memory tools — stubs.

Wired into the registry so agents see them in their tool list, but the
actual MongoDB Atlas Vector Search backend is not implemented yet. Each
function returns `{"status": "not_implemented", ...}` until
`app/services/memory.py` lands.
"""
from __future__ import annotations

from app.tools.base import ToolContext, tool


@tool(
    name="recall",
    description=(
        "Search this agent's private memory (and shared knowledge if scope='shared') "
        "for facts relevant to `query`. Returns up to `limit` snippets ordered "
        "by relevance."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Natural-language query to embed and search."},
            "scope": {
                "type": "string",
                "enum": ["private", "shared", "both"],
                "default": "both",
                "description": "Search this agent's memory, the shared pool, or both.",
            },
            "limit": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
        },
        "required": ["query"],
    },
)
async def recall(ctx: ToolContext, query: str, scope: str = "both", limit: int = 5) -> dict:
    return {"status": "not_implemented", "query": query, "scope": scope, "limit": limit, "results": []}


@tool(
    name="remember",
    description=(
        "Store a fact in memory. Use `visibility='shared'` for facts other "
        "agents should see (e.g. 'customer X prefers email contact'); "
        "use 'private' for agent-internal notes."
    ),
    parameters={
        "type": "object",
        "properties": {
            "fact": {"type": "string", "description": "The fact to remember (one sentence is best)."},
            "visibility": {
                "type": "string",
                "enum": ["private", "shared"],
                "default": "private",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional tags (contact_id, deal_id, topic).",
            },
        },
        "required": ["fact"],
    },
)
async def remember(ctx: ToolContext, fact: str, visibility: str = "private", tags: list[str] | None = None) -> dict:
    return {"status": "not_implemented", "fact": fact, "visibility": visibility, "tags": tags or []}


@tool(
    name="forget",
    description="Delete a previously stored fact by its memory id.",
    parameters={
        "type": "object",
        "properties": {
            "memory_id": {"type": "string", "description": "The id returned from `remember`."},
        },
        "required": ["memory_id"],
    },
)
async def forget(ctx: ToolContext, memory_id: str) -> dict:
    return {"status": "not_implemented", "memory_id": memory_id}
