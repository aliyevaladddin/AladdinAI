# NOTICE: This file is protected under RCF-PL
"""CRM tools for agents.

Provides agent tools to create and manage contacts, batch import leads,
create and track deals, and move deals across pipeline stages.
All actions are scoped to `ctx.user_id`.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import select

from app.models.contact import Contact
from app.models.deal import Deal
from app.services.crm_service import find_or_create_contact
from app.tools.base import ToolContext, tool

log = logging.getLogger(__name__)

DEAL_STAGES = ["lead", "qualified", "proposal", "negotiation", "won", "lost"]


# ── Contacts ─────────────────────────────────────────────────────────────────
# [RCF:PROTECTED]
@tool(
    name="create_contact",
    description=(
        "Create a single contact/client in the CRM. 'name' is required. "
        "Optional fields: 'email', 'phone', 'company', 'tags' (list of strings), 'source', 'notes'."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Full name or company representative name"},
            "email": {"type": "string", "description": "Email address"},
            "phone": {"type": "string", "description": "Phone number"},
            "company": {"type": "string", "description": "Company name"},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of tags (e.g. ['lead', 'enterprise', 'vip'])",
            },
            "source": {"type": "string", "description": "Lead source (e.g. 'agent_created', 'cold_outreach')"},
            "notes": {"type": "string", "description": "Additional notes"},
        },
        "required": ["name"],
    },
)
async def create_contact(
    ctx: ToolContext,
    name: str,
    email: str | None = None,
    phone: str | None = None,
    company: str | None = None,
    tags: list[str] | None = None,
    source: str | None = "agent",
    notes: str | None = None,
) -> dict[str, Any]:
    name = (name or "").strip()
    if not name:
        return {"error": "Contact name is required and cannot be empty."}

    contact = Contact(
        user_id=ctx.user_id,
        name=name,
        email=email.strip() if email else None,
        phone=phone.strip() if phone else None,
        company=company.strip() if company else None,
        tags=tags or [],
        source=source or "agent",
        notes=notes,
    )
    ctx.db.add(contact)
    await ctx.db.commit()
    await ctx.db.refresh(contact)

    try:
        from app.services.webhook_service import trigger_webhooks
        asyncio.create_task(trigger_webhooks(ctx.user_id, "contact_created", {
            "contact_id": contact.id,
            "name": contact.name,
            "email": contact.email,
            "phone": contact.phone,
            "company": contact.company,
        }))
    except Exception:
        pass

    return {
        "status": "created",
        "contact": {
            "id": contact.id,
            "name": contact.name,
            "email": contact.email,
            "phone": contact.phone,
            "company": contact.company,
            "tags": contact.tags,
            "source": contact.source,
        },
    }


# [RCF:PROTECTED]
@tool(
    name="create_contacts_batch",
    description=(
        "Batch create multiple contacts/clients in the CRM in one call (up to 100). "
        "Useful for importing lead lists or entering multiple clients. "
        "Each contact object must have 'name'; optional: 'email', 'phone', 'company', 'tags', 'source', 'notes'."
    ),
    parameters={
        "type": "object",
        "properties": {
            "contacts": {
                "type": "array",
                "description": "List of contacts to create",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Full name"},
                        "email": {"type": "string", "description": "Email address"},
                        "phone": {"type": "string", "description": "Phone number"},
                        "company": {"type": "string", "description": "Company name"},
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags list",
                        },
                        "source": {"type": "string", "description": "Lead source"},
                        "notes": {"type": "string", "description": "Notes"},
                    },
                    "required": ["name"],
                },
            },
        },
        "required": ["contacts"],
    },
)
async def create_contacts_batch(
    ctx: ToolContext,
    contacts: list[dict[str, Any]],
) -> dict[str, Any]:
    if not contacts:
        return {"error": "Contacts list is empty. Provide at least one contact."}

    created: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for idx, item in enumerate(contacts[:100]):
        if not isinstance(item, dict):
            errors.append({"index": idx, "error": "Item must be an object"})
            continue
        raw_name = item.get("name")
        name = str(raw_name).strip() if raw_name is not None else ""
        if not name:
            errors.append({"index": idx, "error": "Missing or empty 'name'"})
            continue

        raw_email = item.get("email")
        raw_phone = item.get("phone")
        raw_company = item.get("company")
        raw_source = item.get("source")
        raw_notes = item.get("notes")
        raw_tags = item.get("tags")

        contact = Contact(
            user_id=ctx.user_id,
            name=name,
            email=str(raw_email).strip() if raw_email else None,
            phone=str(raw_phone).strip() if raw_phone else None,
            company=str(raw_company).strip() if raw_company else None,
            tags=list(raw_tags) if isinstance(raw_tags, list) else [],
            source=str(raw_source).strip() if raw_source else "agent_batch",
            notes=str(raw_notes) if raw_notes else None,
        )
        ctx.db.add(contact)
        created.append(contact)

    if created:
        await ctx.db.commit()
        for c in created:
            await ctx.db.refresh(c)

    return {
        "status": "success",
        "created_count": len(created),
        "contacts": [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "phone": c.phone,
                "company": c.company,
            }
            for c in created
        ],
        "errors": errors,
    }


# [RCF:PROTECTED]
@tool(
    name="list_contacts",
    description=(
        "Search or list contacts in the CRM. "
        "Optional 'search' filters by name, email, or company. 'tag' filters by tag. "
        "Returns up to 'limit' contacts (default 20)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "search": {"type": "string", "description": "Search term for name, email, or company"},
            "tag": {"type": "string", "description": "Filter by tag"},
            "limit": {"type": "integer", "description": "Max contacts to return (default 20, max 100)"},
        },
    },
)
async def list_contacts(
    ctx: ToolContext,
    search: str | None = None,
    tag: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    q = select(Contact).where(Contact.user_id == ctx.user_id)
    if search:
        search_term = f"%{search.strip()}%"
        q = q.where(
            Contact.name.ilike(search_term)
            | Contact.email.ilike(search_term)
            | Contact.company.ilike(search_term)
        )
    q = q.order_by(Contact.updated_at.desc()).limit(min(max(limit, 1), 100))
    result = await ctx.db.execute(q)
    contacts = result.scalars().all()

    if tag:
        contacts = [c for c in contacts if c.tags and tag in c.tags]

    return {
        "count": len(contacts),
        "contacts": [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "phone": c.phone,
                "company": c.company,
                "tags": c.tags or [],
                "source": c.source,
            }
            for c in contacts
        ],
    }


# [RCF:PROTECTED]
@tool(
    name="get_contact",
    description="Get full details of a specific contact by contact_id.",
    parameters={
        "type": "object",
        "properties": {
            "contact_id": {"type": "integer", "description": "ID of the contact"},
        },
        "required": ["contact_id"],
    },
)
async def get_contact(ctx: ToolContext, contact_id: int) -> dict[str, Any]:
    res = await ctx.db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.user_id == ctx.user_id)
    )
    contact = res.scalar_one_or_none()
    if not contact:
        return {"error": f"Contact {contact_id} not found"}
    return {
        "id": contact.id,
        "name": contact.name,
        "email": contact.email,
        "phone": contact.phone,
        "company": contact.company,
        "tags": contact.tags or [],
        "source": contact.source,
        "notes": contact.notes,
        "created_at": contact.created_at.isoformat() if contact.created_at else None,
        "updated_at": contact.updated_at.isoformat() if contact.updated_at else None,
    }


# ── Deals ────────────────────────────────────────────────────────────────────
# [RCF:PROTECTED]
@tool(
    name="create_deal",
    description=(
        "Create a new deal in the CRM sales pipeline. 'title' is required. "
        "To link a contact, pass 'contact_id' (or 'email' / 'phone' / 'name' to auto-find or create the contact). "
        "Stages: lead, qualified, proposal, negotiation, won, lost. Default stage is 'lead'."
    ),
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Deal title (e.g. 'Annual SaaS Contract')"},
            "contact_id": {"type": "integer", "description": "Existing contact ID"},
            "email": {"type": "string", "description": "Customer email (finds or creates contact if contact_id omitted)"},
            "phone": {"type": "string", "description": "Customer phone (finds or creates contact)"},
            "name": {"type": "string", "description": "Customer name for contact creation"},
            "amount": {"type": "number", "description": "Monetary value of the deal"},
            "stage": {
                "type": "string",
                "description": "Pipeline stage: lead, qualified, proposal, negotiation, won, lost (default 'lead')",
            },
            "currency": {"type": "string", "description": "Currency code (default 'USD')"},
            "probability": {"type": "integer", "description": "Estimated win probability 0-100"},
            "notes": {"type": "string", "description": "Notes about this deal"},
        },
        "required": ["title"],
    },
)
async def create_deal(
    ctx: ToolContext,
    title: str,
    contact_id: int | None = None,
    email: str | None = None,
    phone: str | None = None,
    name: str = "",
    amount: float | None = None,
    stage: str = "lead",
    currency: str = "USD",
    probability: int = 0,
    notes: str | None = None,
) -> dict[str, Any]:
    title = (title or "").strip()
    if not title:
        return {"error": "Deal title is required."}

    if stage not in DEAL_STAGES:
        return {"error": f"Invalid stage '{stage}'. Must be one of: {DEAL_STAGES}"}

    # Resolve or create contact if needed
    if contact_id is not None:
        r = await ctx.db.execute(
            select(Contact).where(Contact.id == contact_id, Contact.user_id == ctx.user_id)
        )
        if not r.scalar_one_or_none():
            return {"error": f"Contact {contact_id} not found."}
    elif email or phone:
        contact = await find_or_create_contact(
            ctx.db,
            ctx.user_id,
            identifier=(phone if (phone and not email) else email),
            name=name,
            source="agent_deal",
            is_phone=bool(phone and not email),
        )
        contact_id = contact.id
    elif name:
        contact = Contact(user_id=ctx.user_id, name=name, source="agent_deal")
        ctx.db.add(contact)
        await ctx.db.flush()
        contact_id = contact.id
    else:
        return {"error": "Please provide a contact_id, email, phone, or name to associate with this deal."}

    deal = Deal(
        user_id=ctx.user_id,
        contact_id=contact_id,
        title=title,
        stage=stage,
        amount=float(amount) if amount is not None else None,
        currency=currency or "USD",
        probability=int(probability) if probability else 0,
        assigned_agent_id=ctx.agent_id,
        notes=notes,
    )
    ctx.db.add(deal)
    await ctx.db.commit()
    await ctx.db.refresh(deal)

    try:
        from app.services.webhook_service import trigger_webhooks
        asyncio.create_task(trigger_webhooks(ctx.user_id, "deal_created", {
            "deal_id": deal.id,
            "title": deal.title,
            "amount": deal.amount,
            "stage": deal.stage,
        }))
    except Exception:
        pass

    return {
        "status": "created",
        "deal": {
            "id": deal.id,
            "contact_id": deal.contact_id,
            "title": deal.title,
            "stage": deal.stage,
            "amount": deal.amount,
            "currency": deal.currency,
            "probability": deal.probability,
        },
    }


# [RCF:PROTECTED]
@tool(
    name="create_deals_batch",
    description=(
        "Batch create multiple deals in the CRM pipeline in one call (up to 50). "
        "Each deal object must have 'title' and 'contact_id' (or 'email'/'phone'/'name'). "
        "Optional fields: 'amount', 'stage' (lead, qualified, proposal, negotiation, won, lost), "
        "'currency' (default 'RUB' or 'USD'), 'probability', 'notes'."
    ),
    parameters={
        "type": "object",
        "properties": {
            "deals": {
                "type": "array",
                "description": "List of deals to create",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Deal title (e.g. 'Enterprise License')"},
                        "contact_id": {"type": "integer", "description": "Associated contact ID (e.g. 9 to 28)"},
                        "email": {"type": "string", "description": "Customer email if contact_id omitted"},
                        "phone": {"type": "string", "description": "Customer phone if contact_id omitted"},
                        "name": {"type": "string", "description": "Customer name if creating new contact"},
                        "amount": {"type": "number", "description": "Deal amount in monetary units"},
                        "stage": {
                            "type": "string",
                            "description": "Pipeline stage: lead, qualified, proposal, negotiation, won, lost (default 'lead')",
                        },
                        "currency": {"type": "string", "description": "Currency code (default 'RUB')"},
                        "probability": {"type": "integer", "description": "Win probability 0-100"},
                        "notes": {"type": "string", "description": "Notes on this deal"},
                    },
                    "required": ["title"],
                },
            },
        },
        "required": ["deals"],
    },
)
async def create_deals_batch(
    ctx: ToolContext,
    deals: list[dict[str, Any]],
) -> dict[str, Any]:
    if not deals:
        return {"error": "Deals list is empty. Provide at least one deal."}

    created: list[Deal] = []
    errors: list[dict[str, Any]] = []

    for idx, item in enumerate(deals[:50]):
        if not isinstance(item, dict):
            errors.append({"index": idx, "error": "Item must be a dictionary"})
            continue
        raw_title = item.get("title")
        title = str(raw_title).strip() if raw_title is not None else ""
        if not title:
            errors.append({"index": idx, "error": "Missing or empty 'title'"})
            continue

        raw_stage = str(item.get("stage") or "lead").strip().lower()
        stage = raw_stage if raw_stage in DEAL_STAGES else "lead"

        contact_id = item.get("contact_id")
        email = item.get("email")
        phone = item.get("phone")
        name = item.get("name")

        if contact_id is not None:
            try:
                contact_id = int(contact_id)
            except (ValueError, TypeError):
                contact_id = None

        if contact_id is None and (email or phone):
            contact = await find_or_create_contact(
                ctx.db,
                ctx.user_id,
                identifier=(phone if (phone and not email) else email),
                name=name or "",
                source="agent_deal_batch",
                is_phone=bool(phone and not email),
            )
            contact_id = contact.id
        elif contact_id is None and name:
            contact = Contact(user_id=ctx.user_id, name=name, source="agent_deal_batch")
            ctx.db.add(contact)
            await ctx.db.flush()
            contact_id = contact.id

        if contact_id is None:
            errors.append({"index": idx, "title": title, "error": "No valid contact_id or contact details provided"})
            continue

        raw_amount = item.get("amount")
        try:
            amount = float(raw_amount) if raw_amount is not None else None
        except (ValueError, TypeError):
            amount = None

        raw_prob = item.get("probability")
        try:
            probability = int(raw_prob) if raw_prob is not None else 0
        except (ValueError, TypeError):
            probability = 0

        currency = str(item.get("currency") or "RUB").strip()
        notes = str(item.get("notes")) if item.get("notes") else None

        deal = Deal(
            user_id=ctx.user_id,
            contact_id=contact_id,
            title=title,
            stage=stage,
            amount=amount,
            currency=currency,
            probability=probability,
            assigned_agent_id=ctx.agent_id,
            notes=notes,
        )
        ctx.db.add(deal)
        created.append(deal)

    if created:
        await ctx.db.commit()
        for d in created:
            await ctx.db.refresh(d)

    return {
        "status": "success",
        "created_count": len(created),
        "deals": [
            {
                "id": d.id,
                "contact_id": d.contact_id,
                "title": d.title,
                "stage": d.stage,
                "amount": d.amount,
                "currency": d.currency,
            }
            for d in created
        ],
        "errors": errors,
    }


# [RCF:PROTECTED]
@tool(
    name="list_deals",
    description=(
        "List deals in the sales pipeline. Optional 'stage' filters by stage: "
        "lead, qualified, proposal, negotiation, won, lost. "
        "Optional 'contact_id' filters by contact. Returns up to 'limit' deals."
    ),
    parameters={
        "type": "object",
        "properties": {
            "stage": {"type": "string", "description": "Filter by stage"},
            "contact_id": {"type": "integer", "description": "Filter by contact ID"},
            "limit": {"type": "integer", "description": "Max deals to return (default 20, max 100)"},
        },
    },
)
async def list_deals(
    ctx: ToolContext,
    stage: str | None = None,
    contact_id: int | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    q = select(Deal).where(Deal.user_id == ctx.user_id)
    if stage:
        q = q.where(Deal.stage == stage)
    if contact_id is not None:
        q = q.where(Deal.contact_id == contact_id)
    q = q.order_by(Deal.updated_at.desc()).limit(min(max(limit, 1), 100))
    res = await ctx.db.execute(q)
    deals = res.scalars().all()

    return {
        "count": len(deals),
        "deals": [
            {
                "id": d.id,
                "contact_id": d.contact_id,
                "title": d.title,
                "stage": d.stage,
                "amount": d.amount,
                "currency": d.currency,
                "probability": d.probability,
                "assigned_agent_id": d.assigned_agent_id,
            }
            for d in deals
        ],
    }


# [RCF:PROTECTED]
@tool(
    name="update_deal_stage",
    description=(
        "Move a deal to a new stage in the CRM pipeline. "
        "Stages: lead, qualified, proposal, negotiation, won, lost."
    ),
    parameters={
        "type": "object",
        "properties": {
            "deal_id": {"type": "integer", "description": "ID of the deal"},
            "stage": {
                "type": "string",
                "description": "New pipeline stage: lead, qualified, proposal, negotiation, won, lost",
            },
            "notes": {"type": "string", "description": "Optional notes or reason for stage change"},
        },
        "required": ["deal_id", "stage"],
    },
)
async def update_deal_stage(
    ctx: ToolContext,
    deal_id: int,
    stage: str,
    notes: str | None = None,
) -> dict[str, Any]:
    if stage not in DEAL_STAGES:
        return {"error": f"Invalid stage '{stage}'. Must be one of: {DEAL_STAGES}"}

    res = await ctx.db.execute(
        select(Deal).where(Deal.id == deal_id, Deal.user_id == ctx.user_id)
    )
    deal = res.scalar_one_or_none()
    if not deal:
        return {"error": f"Deal {deal_id} not found."}

    old_stage = deal.stage
    deal.stage = stage
    if notes:
        deal.notes = f"{deal.notes}\n{notes}".strip() if deal.notes else notes
    await ctx.db.commit()
    await ctx.db.refresh(deal)

    try:
        from app.services.webhook_service import trigger_webhooks
        asyncio.create_task(trigger_webhooks(ctx.user_id, "deal_updated", {
            "deal_id": deal.id,
            "title": deal.title,
            "old_stage": old_stage,
            "new_stage": stage,
        }))
    except Exception:
        pass

    return {
        "status": "updated",
        "deal_id": deal.id,
        "old_stage": old_stage,
        "new_stage": deal.stage,
    }
