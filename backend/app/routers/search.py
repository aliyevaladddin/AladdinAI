"""Global search across contacts, deals, and activities (emails/messages).

Returns a flat list of `SearchResult` items, each tagged with its `kind` so the
frontend can render and route to the right page.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.activity import Activity
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.user import User
from app.security import get_current_user

router = APIRouter(prefix="/search", tags=["search"])


class SearchResult(BaseModel):
    kind: Literal["contact", "deal", "activity"]
    id: int
    title: str
    subtitle: str | None = None
    snippet: str | None = None
    # Routing hints for the frontend
    contact_id: int | None = None
    activity_type: str | None = None
    channel: str | None = None
    created_at: datetime | None = None


class SearchResponse(BaseModel):
    contacts: list[SearchResult]
    deals: list[SearchResult]
    activities: list[SearchResult]
    total: int


@router.get("", response_model=SearchResponse)
async def global_search(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(8, ge=1, le=30),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    term = f"%{q.strip()}%"

    # Contacts
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

    # Deals
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

    # Activities — emails and messages
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
        # Strip HTML noise from the snippet for messages with rich content
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

    return SearchResponse(
        contacts=contacts,
        deals=deals,
        activities=activities,
        total=len(contacts) + len(deals) + len(activities),
    )
