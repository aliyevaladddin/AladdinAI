"""Memory tools — backed by `app.services.memory` (MongoDB Atlas Vector Search).

Three tools: recall (vector search), remember (store), forget (delete).
Visibility model:
  - private: scoped to the calling agent_id
  - shared:  visible to all agents owned by this user

All errors are caught and returned as `{"error": "..."}` so the LLM keeps
iterating instead of crashing the tool-call loop.
"""
from __future__ import annotations

from sqlalchemy import select

from app.models.agent import Agent
from app.services import memory as mem_service
from app.services.gates import gate_memory_write, gate_recall_rerank
from app.services.memory import MemoryError
from app.services.safety import safety_pii
from app.tools.base import ToolContext, tool


async def _load_agent(ctx: ToolContext) -> Agent | None:
    if ctx.agent_id is None:
        return None
    return (await ctx.db.execute(
        select(Agent).where(Agent.id == ctx.agent_id)
    )).scalar_one_or_none()


@tool(
    name="recall",
    description=(
        "Search this agent's private memory (and shared knowledge if scope='shared' or 'both') "
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
    try:
        results = await mem_service.search_memory(
            ctx.db,
            user_id=ctx.user_id,
            agent_id=ctx.agent_id,
            query=query,
            scope=scope,
            limit=limit,
        )
    except MemoryError as e:
        return {"error": str(e), "results": []}

    agent = await _load_agent(ctx)
    if agent is not None and results:
        results = await gate_recall_rerank(
            ctx.db, agent=agent, query=query, results=results, limit=limit
        )

    return {
        "query": query,
        "scope": scope,
        "count": len(results),
        "results": [
            {
                "id": r["id"],
                "fact": r["fact"],
                "tags": r["tags"],
                "visibility": r["visibility"],
                "score": round(r["score"], 4),
            }
            for r in results
        ],
    }


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
async def remember(
    ctx: ToolContext,
    fact: str,
    visibility: str = "private",
    tags: list[str] | None = None,
) -> dict:
    agent = await _load_agent(ctx)
    redacted_labels: list[str] = []
    if agent is not None:
        verdict = await gate_memory_write(
            ctx.db, agent=agent, fact=fact, visibility=visibility
        )
        if not verdict["save"]:
            return {"status": "skipped", "reason": verdict.get("reason", "filtered_by_gate")}

        pii = await safety_pii(ctx.db, agent=agent, text=fact, phase="memory_write")
        if pii["redacted"]:
            fact = pii["text"]
            redacted_labels = pii["labels"]

    try:
        result = await mem_service.store_memory(
            ctx.db,
            user_id=ctx.user_id,
            agent_id=ctx.agent_id,
            fact=fact,
            visibility=visibility,
            tags=tags,
            session_id=ctx.session_id,
        )
    except MemoryError as e:
        return {"error": str(e)}

    return {
        "status": "stored",
        "id": result["id"],
        "visibility": result["visibility"],
        "pii_redacted": redacted_labels or None,
    }


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
    try:
        deleted = await mem_service.delete_memory(
            ctx.db,
            user_id=ctx.user_id,
            agent_id=ctx.agent_id,
            memory_id=memory_id,
        )
    except MemoryError as e:
        return {"error": str(e)}
    return {"status": "deleted" if deleted else "not_found", "memory_id": memory_id}
