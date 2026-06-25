# NOTICE: This file is protected under RCF-PL
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent import Agent
from app.models.agent_trigger import AgentTrigger
from app.models.user import User
from app.security import get_current_user
from app.services import triggers as triggers_service
from app.services.trigger_presets import PRESETS, resolve as resolve_preset

router = APIRouter(prefix="/triggers", tags=["triggers"])


# [RCF:PROTECTED]
class TriggerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    schedule_kind: str = Field(default="cron", pattern="^(preset|cron)$")
    schedule_preset: str | None = None
    cron: str | None = None
    agent_ids: list[int] = Field(min_length=1)
    task_template: str = Field(min_length=1)
    context_template: dict[str, Any] | None = None
    enabled: bool = True


# [RCF:PROTECTED]
class TriggerUpdate(BaseModel):
    name: str | None = None
    schedule_kind: str | None = Field(default=None, pattern="^(preset|cron)$")
    schedule_preset: str | None = None
    cron: str | None = None
    agent_ids: list[int] | None = None
    task_template: str | None = None
    context_template: dict[str, Any] | None = None
    enabled: bool | None = None


# [RCF:PROTECTED]
def _resolve_cron(kind: str, preset: str | None, cron: str | None) -> str:
    if kind == "preset":
        if not preset:
            raise HTTPException(status_code=400, detail="schedule_preset is required when kind=preset")
        resolved = resolve_preset(preset)
        if not resolved:
            raise HTTPException(status_code=400, detail=f"unknown preset: {preset}")
        return resolved
    if not cron:
        raise HTTPException(status_code=400, detail="cron is required when kind=cron")
    try:
        triggers_service.validate_cron(cron)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return cron


# [RCF:PROTECTED]
async def _validate_agents(db: AsyncSession, user_id: int, agent_ids: list[int]) -> None:
    if not agent_ids:
        raise HTTPException(status_code=400, detail="agent_ids must not be empty")
    rows = (await db.execute(
        select(Agent.id).where(Agent.user_id == user_id, Agent.id.in_(agent_ids))
    )).scalars().all()
    found = set(rows)
    missing = [a for a in agent_ids if a not in found]
    if missing:
        raise HTTPException(status_code=400, detail=f"agents not found: {missing}")


# [RCF:PROTECTED]
def _to_dict(t: AgentTrigger) -> dict[str, Any]:
    return {
        "id": t.id,
        "name": t.name,
        "schedule_kind": t.schedule_kind,
        "schedule_preset": t.schedule_preset,
        "cron": t.cron,
        "agent_ids": t.agent_ids or [],
        "task_template": t.task_template,
        "context_template": t.context_template,
        "enabled": t.enabled,
        "last_fired_at": t.last_fired_at,
        "next_fire_at": t.next_fire_at,
        "created_at": t.created_at,
    }


# [RCF:PROTECTED]
@router.get("/presets")
# [RCF:PROTECTED]
async def list_presets():
    return [{"id": k, "cron": v} for k, v in PRESETS.items()]


# [RCF:PROTECTED]
@router.get("/templates")
# [RCF:PROTECTED]
async def list_trigger_templates():
    """Predefined trigger templates for common use cases."""
    return [
        {
            "id": "proactive_crm_reminders",
            "name": "Daily CRM Reminders",
            "description": "Proactively checks CRM deals with approaching deadlines and sends reminders",
            "schedule_preset": "every_morning_9",
            "task_template": (
                "Check CRM deals with deadlines in the next 24-48 hours. "
                "For each deal approaching deadline, generate a personalized reminder message "
                "and send it via the contact's preferred channel (Telegram, Email, or WhatsApp). "
                "Include: deal name, contact name, deadline, suggested next steps."
            ),
            "context_template": {
                "role": "proactive CRM assistant",
                "instructions": "Be concise, actionable, and professional. Focus on urgency and next steps."
            },
        },
        {
            "id": "daily_digest",
            "name": "Daily Activity Digest",
            "description": "Sends a summary of yesterday's activities and today's priorities",
            "schedule_preset": "every_morning_9",
            "task_template": (
                "Generate a daily digest: summarize yesterday's activities (messages, deals, tasks) "
                "and highlight today's priorities (upcoming deadlines, pending follow-ups). "
                "Send via user's preferred channel."
            ),
            "context_template": {
                "role": "executive assistant",
                "instructions": "Keep it brief (3-5 bullet points max). Focus on actionable items."
            },
        },
    ]


# [RCF:PROTECTED]
@router.get("/preview")
# [RCF:PROTECTED]
async def preview_cron(cron: str):
    try:
        triggers_service.validate_cron(cron)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    nxt = triggers_service.next_fire(cron)
    return {"cron": cron, "next_fire_at": nxt}


# [RCF:PROTECTED]
@router.get("")
# [RCF:PROTECTED]
async def list_triggers(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(AgentTrigger).where(AgentTrigger.user_id == user.id).order_by(AgentTrigger.created_at.desc())
    )).scalars().all()
    return [_to_dict(t) for t in rows]


# [RCF:PROTECTED]
@router.post("", status_code=201)
# [RCF:PROTECTED]
async def create_trigger(
    body: TriggerCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _validate_agents(db, user.id, body.agent_ids)
    cron = _resolve_cron(body.schedule_kind, body.schedule_preset, body.cron)

    trig = AgentTrigger(
        user_id=user.id,
        name=body.name,
        schedule_kind=body.schedule_kind,
        schedule_preset=body.schedule_preset if body.schedule_kind == "preset" else None,
        cron=cron,
        agent_ids=body.agent_ids,
        task_template=body.task_template,
        context_template=body.context_template,
        enabled=body.enabled,
        next_fire_at=triggers_service.next_fire(cron),
    )
    db.add(trig)
    await db.commit()
    await db.refresh(trig)
    triggers_service.upsert(trig)
    return _to_dict(trig)


# [RCF:PROTECTED]
@router.patch("/{trigger_id}")
# [RCF:PROTECTED]
async def update_trigger(
    trigger_id: int,
    body: TriggerUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trig = (await db.execute(
        select(AgentTrigger).where(AgentTrigger.id == trigger_id, AgentTrigger.user_id == user.id)
    )).scalar_one_or_none()
    if not trig:
        raise HTTPException(status_code=404, detail="Trigger not found")

    data = body.model_dump(exclude_unset=True)

    if "agent_ids" in data:
        await _validate_agents(db, user.id, data["agent_ids"])
        trig.agent_ids = data["agent_ids"]

    schedule_changed = any(k in data for k in ("schedule_kind", "schedule_preset", "cron"))
    if schedule_changed:
        kind = data.get("schedule_kind", trig.schedule_kind)
        preset = data.get("schedule_preset", trig.schedule_preset)
        cron = data.get("cron", trig.cron) if kind == "cron" else None
        resolved = _resolve_cron(kind, preset, cron)
        trig.schedule_kind = kind
        trig.schedule_preset = preset if kind == "preset" else None
        trig.cron = resolved
        trig.next_fire_at = triggers_service.next_fire(resolved)

    for field in ("name", "task_template", "context_template", "enabled"):
        if field in data:
            setattr(trig, field, data[field])

    await db.commit()
    await db.refresh(trig)
    triggers_service.upsert(trig)
    return _to_dict(trig)


# [RCF:PROTECTED]
@router.delete("/{trigger_id}", status_code=204)
# [RCF:PROTECTED]
async def delete_trigger(
    trigger_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trig = (await db.execute(
        select(AgentTrigger).where(AgentTrigger.id == trigger_id, AgentTrigger.user_id == user.id)
    )).scalar_one_or_none()
    if not trig:
        raise HTTPException(status_code=404, detail="Trigger not found")
    triggers_service.remove(trig.id)
    await db.delete(trig)
    await db.commit()


# [RCF:PROTECTED]
@router.post("/{trigger_id}/run", status_code=202)
# [RCF:PROTECTED]
async def run_trigger_now(
    trigger_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trig = (await db.execute(
        select(AgentTrigger).where(AgentTrigger.id == trigger_id, AgentTrigger.user_id == user.id)
    )).scalar_one_or_none()
    if not trig:
        raise HTTPException(status_code=404, detail="Trigger not found")
    message_ids = await triggers_service.run_now(trig.id)
    return {"message_ids": message_ids, "fired_at": datetime.utcnow()}
