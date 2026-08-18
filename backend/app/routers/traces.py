# NOTICE: This file is protected under RCF-PL
"""Global traces listing — all agent traces for the authenticated user.

Unlike the per-agent ``GET /api/agents/{id}/traces`` endpoint, this returns
traces across every agent in a single paginated view and enriches each row
with the agent's name.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent import Agent
from app.models.user import User
from app.security import get_current_user
from app.services.memory import MemoryError as MemSvcError
from app.services.memory import get_mongo_db
from app.services.tracing import TRACE_COLLECTION

router = APIRouter(prefix="/traces", tags=["traces"])


def _serialise(doc: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in doc.items():
        if k == "_id":
            out["id"] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


@router.get("")
async def list_all_traces(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    outcome: str | None = Query(default=None, pattern=r"^[a-z_]{1,50}$"),
    agent_id: int | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List agent traces across all of the user's agents (newest first)."""
    # 1. Resolve all agent IDs and names for this user
    agents_result = await db.execute(
        select(Agent.id, Agent.name).where(Agent.user_id == user.id)
    )
    agents_map = {row.id: row.name for row in agents_result.all()}

    if not agents_map:
        return {"total": 0, "offset": 0, "limit": limit, "items": []}

    # 2. Query Mongo — scoped to user, optionally narrowed to one agent
    try:
        mdb = await get_mongo_db(db, user.id)
    except MemSvcError:
        raise HTTPException(
            status_code=400,
            detail="No MongoDB cluster configured — connect one first.",
        )

    query: dict[str, Any] = {"user_id": user.id}
    if agent_id is not None:
        if agent_id not in agents_map:
            raise HTTPException(status_code=404, detail="Agent not found")
        query["agent_id"] = agent_id
    if outcome:
        query["outcome"] = outcome

    collection = mdb[TRACE_COLLECTION]
    total = await collection.count_documents(query)
    cursor = (
        collection.find(query, projection={"messages": 0})
        .sort("created_at", -1)
        .skip(offset)
        .limit(limit)
    )

    items = []
    async for doc in cursor:
        item = _serialise(doc)
        # Enrich with agent name
        aid = item.get("agent_id")
        item["agent_name"] = agents_map.get(aid, f"Agent #{aid}")
        items.append(item)

    return {"total": total, "offset": offset, "limit": limit, "items": items}
