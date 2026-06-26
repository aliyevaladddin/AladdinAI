# NOTICE: This file is protected under RCF-PL
"""Global search across contacts, deals, activities, agents, and memory.

Returns a structured `SearchResponse` with each section tagged by `kind` so
the frontend can render and navigate to the right page.

Memory search uses MongoDB regex (list_memories with q=) — no embedding
provider required, graceful no-op if MongoDB is not configured.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.activity import Activity
from app.models.agent import Agent
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.user import User
from app.security import get_current_user

log = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


# [RCF:PROTECTED]
class SearchResult(BaseModel):
    kind: Literal["contact", "deal", "activity", "agent", "memory"]
    id: int
    title: str
    subtitle: str | None = None
    snippet: str | None = None
    # Routing hints for the frontend
    contact_id: int | None = None
    activity_type: str | None = None
    channel: str | None = None
    created_at: datetime | None = None


# [RCF:PROTECTED]
class SearchResponse(BaseModel):
    contacts: list[SearchResult]
    deals: list[SearchResult]
    activities: list[SearchResult]
    agents: list[SearchResult]
    memories: list[SearchResult]
    total: int


# [RCF:PROTECTED]
@router.get("", response_model=SearchResponse)
# [RCF:PROTECTED]
async def global_search(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(8, ge=1, le=30),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    term = f"%{q.strip()}%"

    # ── Contacts ──────────────────────────────────────────────────────────────
    contact_rows = (
        await db.execute(
            select(Contact)
            .where(
                Contact.user_id == user.id,
                or_(
                    Contact.name.ilike(term),
                    Contact.email.ilike(term),
                    Contact.company.ilike(term),
                    Contact.phone.ilike(term),
                ),
            )
            .order_by(Contact.updated_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    contacts = [
        SearchResult(
            kind="contact",
            id=c.id,
            title=c.name,
            subtitle=c.email or c.company or c.phone,
            contact_id=c.id,
        )
        for c in contact_rows
    ]

    # ── Deals ─────────────────────────────────────────────────────────────────
    deal_rows = (
        await db.execute(
            select(Deal)
            .where(
                Deal.user_id == user.id,
                or_(Deal.title.ilike(term), Deal.notes.ilike(term)),
            )
            .order_by(Deal.updated_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    deals = [
        SearchResult(
            kind="deal",
            id=d.id,
            title=d.title,
            subtitle=f"{d.stage} • {d.currency} {d.amount or 0:.0f}",
            contact_id=d.contact_id,
        )
        for d in deal_rows
    ]

    # ── Activities — emails and messages ──────────────────────────────────────
    activity_rows = (
        await db.execute(
            select(Activity)
            .where(
                Activity.user_id == user.id,
                or_(Activity.subject.ilike(term), Activity.content.ilike(term)),
            )
            .order_by(Activity.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    activities: list[SearchResult] = []
    for a in activity_rows:
        snippet = (a.content or "").replace("\n", " ")
        if "<" in snippet:
            import re
            snippet = re.sub(r"<[^>]+>", " ", snippet)
            snippet = re.sub(r"\s{2,}", " ", snippet)
        snippet = snippet.strip()[:120]
        activities.append(
            SearchResult(
                kind="activity",
                id=a.id,
                title=a.subject or "(no subject)",
                subtitle=(a.channel or a.type or "").replace("_", " "),
                snippet=snippet or None,
                contact_id=a.contact_id,
                activity_type=a.type,
                channel=a.channel,
                created_at=a.created_at,
            )
        )

    # ── Agents ────────────────────────────────────────────────────────────────
    agent_rows = (
        await db.execute(
            select(Agent)
            .where(
                Agent.user_id == user.id,
                or_(
                    Agent.name.ilike(term),
                    Agent.role.ilike(term),
                    Agent.model.ilike(term),
                ),
            )
            .order_by(Agent.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    agents = [
        SearchResult(
            kind="agent",
            id=a.id,
            title=a.name,
            subtitle=f"{a.role} · {a.model}",
            snippet=f"Status: {a.status}",
        )
        for a in agent_rows
    ]

    # ── Memory search (MongoDB regex — graceful no-op if not configured) ──────
    memories: list[SearchResult] = []
    try:
        from app.services.memory import list_memories
        mem_docs = await list_memories(
            db,
            user_id=user.id,
            agent_id=None,   # None + scope=shared searches shared context
            scope="shared",
            q=q.strip(),
            limit=limit,
        )
        # Also search private memories across all agents
        agent_ids_result = await db.execute(
            select(Agent.id).where(Agent.user_id == user.id)
        )
        for agent_id in agent_ids_result.scalars().all():
            private_docs = await list_memories(
                db,
                user_id=user.id,
                agent_id=agent_id,
                scope="private",
                q=q.strip(),
                limit=3,
            )
            mem_docs.extend(private_docs)

        # Deduplicate by id and build results (use index as synthetic int id)
        seen: set[str] = set()
        for idx, doc in enumerate(mem_docs):
            doc_id = doc.get("id", "")
            if doc_id in seen:
                continue
            seen.add(doc_id)
            fact = (doc.get("fact") or "").strip()
            if not fact:
                continue
            tags = doc.get("tags") or []
            memories.append(
                SearchResult(
                    kind="memory",
                    id=idx + 1,          # synthetic int id for the frontend key
                    title=fact[:80] + ("…" if len(fact) > 80 else ""),
                    subtitle=", ".join(tags) if tags else (
                        "private" if doc.get("agent_id") else "shared"
                    ),
                    snippet=fact[:160] if len(fact) > 80 else None,
                )
            )
        memories = memories[:limit]
    except Exception as exc:
        # MongoDB not configured or Atlas unreachable — silently skip
        log.debug("Memory search skipped: %s", exc)

    return SearchResponse(
        contacts=contacts,
        deals=deals,
        activities=activities,
        agents=agents,
        memories=memories,
        total=len(contacts) + len(deals) + len(activities) + len(agents) + len(memories),
    )
