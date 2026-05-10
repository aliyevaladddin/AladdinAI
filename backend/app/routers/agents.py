from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.database import async_session, get_db
from app.models.agent import Agent
from app.models.agent_message import AgentMessage
from app.models.activity import Activity
from app.models.agent_trigger import AgentTrigger
from app.models.user import User
from app.schemas.agents import AgentCreate, AgentResponse, AgentUpdate
from app.security import get_current_user
import json as _json

from app.models.llm_provider import LLMProvider
from app.services import gate_log, memory as memory_service
from app.services.agent_runner import run_agent
from app.services.llm_service import LLMError
from app.services.memory import MemoryError as MemoryServiceError
from app.services.recommended_models import (
    resolve_extraction as resolve_extraction_recs,
    resolve_gates as resolve_gates_recs,
    resolve_safety as resolve_safety_recs,
)

GATE_NAMES = {"handoff", "memory_write", "recall_rerank"}
SAFETY_NAMES = {"ingress", "egress", "pii"}


class GatesUpdate(BaseModel):
    default_gate_model: str | None = None
    gates: dict[str, dict[str, Any]] | None = None  # {name: {enabled: bool, model: str|null}}


class SafetyUpdate(BaseModel):
    default_safety_model: str | None = None
    safety_block_response: str | None = None
    safety: dict[str, dict[str, Any]] | None = None


class ExtractionUpdate(BaseModel):
    enabled: bool | None = None
    model: str | None = None
    max_facts: int | None = None


class MemoryCreate(BaseModel):
    fact: str
    visibility: str = "private"
    tags: list[str] | None = None

router = APIRouter(prefix="/agents", tags=["agents"])


class InboxRequest(BaseModel):
    task: str
    context: dict | None = None
    parent_session_id: int | None = None


class InboxResponse(BaseModel):
    message_id: int
    status: str


@router.get("/{agent_id}/stats")
async def get_agent_stats(
    agent_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return real-time agentic stats for an agent."""
    from sqlalchemy import func as sa_func

    agent = (await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id)
    )).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    now = datetime.now(timezone.utc)

    # Uptime: time since agent was created if running, otherwise 0
    uptime_seconds = 0
    if agent.status in ("running", "active"):
        delta = now - agent.created_at.replace(tzinfo=timezone.utc) if agent.created_at.tzinfo is None else now - agent.created_at
        uptime_seconds = int(delta.total_seconds())

    # Total tasks (completed agent_messages)
    total_tasks_res = await db.execute(
        select(sa_func.count(AgentMessage.id)).where(
            AgentMessage.to_agent_id == agent_id,
            AgentMessage.user_id == user.id,
            AgentMessage.status == "done",
        )
    )
    total_tasks = total_tasks_res.scalar() or 0

    # Token usage estimate: sum of lengths of task + result in completed messages
    # Rough estimate: 1 token ≈ 4 characters
    msgs_res = await db.execute(
        select(AgentMessage).where(
            AgentMessage.to_agent_id == agent_id,
            AgentMessage.user_id == user.id,
            AgentMessage.status == "done",
        )
    )
    total_chars = 0
    for m in msgs_res.scalars().all():
        total_chars += len(m.task or "")
        total_chars += len(m.result or "")
    estimated_tokens = total_chars // 4

    # Gate decisions count
    gate_decisions_count = 0
    try:
        decisions = await gate_log.list_decisions(db, user_id=user.id, agent_id=agent_id, limit=1000)
        gate_decisions_count = len(decisions)
    except Exception:
        pass

    # Format uptime for display
    if uptime_seconds < 3600:
        uptime_display = f"{uptime_seconds // 60}m"
    elif uptime_seconds < 86400:
        hours = uptime_seconds / 3600
        uptime_display = f"{hours:.1f}h"
    else:
        days = uptime_seconds / 86400
        uptime_display = f"{days:.1f}d"

    # Format tokens for display
    if estimated_tokens >= 1_000_000:
        tokens_display = f"{estimated_tokens / 1_000_000:.1f}M"
    elif estimated_tokens >= 1000:
        tokens_display = f"{estimated_tokens / 1000:.1f}k"
    else:
        tokens_display = str(estimated_tokens)

    return {
        "uptime_seconds": uptime_seconds,
        "uptime_display": uptime_display,
        "estimated_tokens": estimated_tokens,
        "tokens_display": tokens_display,
        "total_tasks": total_tasks,
        "gate_decisions": gate_decisions_count,
    }


@router.get("", response_model=list[AgentResponse])
async def list_agents(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.user_id == user.id))
    return result.scalars().all()


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(body: AgentCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    agent = Agent(user_id=user.id, **body.model_dump())
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: int, body: AgentUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(agent, key, value)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await db.delete(agent)
    await db.commit()


@router.post("/{agent_id}/start")
async def start_agent(agent_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.status = "running"
    await db.commit()
    return {"status": "running", "agent": agent.name}


@router.post("/{agent_id}/stop")
async def stop_agent(agent_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.status = "stopped"
    await db.commit()
    return {"status": "stopped", "agent": agent.name}


@router.post("/{agent_id}/inbox", response_model=InboxResponse, status_code=202)
async def agent_inbox(
    agent_id: int,
    body: InboxRequest,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Queue a delegated task for an agent. Worker processes it async."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    msg = AgentMessage(
        user_id=user.id,
        from_agent_id=None,
        to_agent_id=agent.id,
        parent_session_id=body.parent_session_id,
        task=body.task,
        context=body.context,
        status="pending",
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    background.add_task(_process_agent_message, msg.id)
    return InboxResponse(message_id=msg.id, status="pending")


@router.get("/{agent_id}/messages")
async def list_agent_messages(
    agent_id: int,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AgentMessage)
        .where(AgentMessage.to_agent_id == agent_id, AgentMessage.user_id == user.id)
        .order_by(AgentMessage.created_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "id": m.id,
            "from_agent_id": m.from_agent_id,
            "to_agent_id": m.to_agent_id,
            "task": m.task,
            "status": m.status,
            "result": m.result,
            "error": m.error,
            "created_at": m.created_at,
            "completed_at": m.completed_at,
        }
        for m in rows
    ]


@router.get("/{agent_id}/gates")
async def get_agent_gates(
    agent_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = (await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id)
    )).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    cfg = agent.tools_config or {}
    gates = cfg.get("gates") or {}
    return {
        "default_gate_model": cfg.get("default_gate_model"),
        "gates": {
            name: {
                "enabled": bool((gates.get(name) or {}).get("enabled", False)),
                "model": (gates.get(name) or {}).get("model"),
            }
            for name in GATE_NAMES
        },
    }


@router.patch("/{agent_id}/gates")
async def patch_agent_gates(
    agent_id: int,
    body: GatesUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = (await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id)
    )).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    cfg = dict(agent.tools_config or {})
    if body.default_gate_model is not None:
        cfg["default_gate_model"] = body.default_gate_model or None

    if body.gates is not None:
        existing = dict(cfg.get("gates") or {})
        for name, settings in body.gates.items():
            if name not in GATE_NAMES:
                raise HTTPException(status_code=400, detail=f"Unknown gate: {name}")
            current = dict(existing.get(name) or {})
            if "enabled" in settings:
                current["enabled"] = bool(settings["enabled"])
            if "model" in settings:
                current["model"] = settings["model"] or None
            existing[name] = current
        cfg["gates"] = existing

    agent.tools_config = cfg
    flag_modified(agent, "tools_config")
    await db.commit()
    await db.refresh(agent)

    gates = cfg.get("gates") or {}
    return {
        "default_gate_model": cfg.get("default_gate_model"),
        "gates": {
            name: {
                "enabled": bool((gates.get(name) or {}).get("enabled", False)),
                "model": (gates.get(name) or {}).get("model"),
            }
            for name in GATE_NAMES
        },
    }


@router.get("/{agent_id}/safety")
async def get_agent_safety(
    agent_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = (await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id)
    )).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    cfg = agent.tools_config or {}
    safety = cfg.get("safety") or {}
    return {
        "default_safety_model": cfg.get("default_safety_model"),
        "safety_block_response": cfg.get("safety_block_response"),
        "safety": {
            name: {
                "enabled": bool((safety.get(name) or {}).get("enabled", False)),
                "model": (safety.get(name) or {}).get("model"),
            }
            for name in SAFETY_NAMES
        },
    }


@router.patch("/{agent_id}/safety")
async def patch_agent_safety(
    agent_id: int,
    body: SafetyUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = (await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id)
    )).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    cfg = dict(agent.tools_config or {})
    if body.default_safety_model is not None:
        cfg["default_safety_model"] = body.default_safety_model or None
    if body.safety_block_response is not None:
        cfg["safety_block_response"] = body.safety_block_response or None

    if body.safety is not None:
        existing = dict(cfg.get("safety") or {})
        for name, settings in body.safety.items():
            if name not in SAFETY_NAMES:
                raise HTTPException(status_code=400, detail=f"Unknown safety check: {name}")
            current = dict(existing.get(name) or {})
            if "enabled" in settings:
                current["enabled"] = bool(settings["enabled"])
            if "model" in settings:
                current["model"] = settings["model"] or None
            existing[name] = current
        cfg["safety"] = existing

    agent.tools_config = cfg
    flag_modified(agent, "tools_config")
    await db.commit()
    await db.refresh(agent)

    safety = cfg.get("safety") or {}
    return {
        "default_safety_model": cfg.get("default_safety_model"),
        "safety_block_response": cfg.get("safety_block_response"),
        "safety": {
            name: {
                "enabled": bool((safety.get(name) or {}).get("enabled", False)),
                "model": (safety.get(name) or {}).get("model"),
            }
            for name in SAFETY_NAMES
        },
    }


async def _provider_catalog(db: AsyncSession, agent: Agent) -> list[str]:
    if not agent.llm_provider_id:
        return []
    provider = (await db.execute(
        select(LLMProvider).where(LLMProvider.id == agent.llm_provider_id)
    )).scalar_one_or_none()
    if not provider or not provider.models_available:
        return []
    try:
        models = _json.loads(provider.models_available)
    except (TypeError, ValueError):
        return []
    return [m for m in models if isinstance(m, str)]


@router.get("/{agent_id}/safety/recommendations")
async def get_agent_safety_recommendations(
    agent_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = (await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id)
    )).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    catalog = await _provider_catalog(db, agent)
    return {"recommendations": resolve_safety_recs(catalog), "catalog_size": len(catalog)}


@router.get("/{agent_id}/gates/recommendations")
async def get_agent_gates_recommendations(
    agent_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = (await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id)
    )).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    catalog = await _provider_catalog(db, agent)
    return {"recommendations": resolve_gates_recs(catalog), "catalog_size": len(catalog)}


@router.get("/{agent_id}/extraction/recommendations")
async def get_agent_extraction_recommendations(
    agent_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = (await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id)
    )).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    catalog = await _provider_catalog(db, agent)
    return {"recommendation": resolve_extraction_recs(catalog), "catalog_size": len(catalog)}


@router.get("/{agent_id}/extraction")
async def get_agent_extraction(
    agent_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = (await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id)
    )).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    cfg = agent.tools_config or {}
    sub = cfg.get("extraction") or {}
    return {
        "enabled": bool(sub.get("enabled", False)),
        "model": sub.get("model"),
        "max_facts": sub.get("max_facts"),
    }


@router.patch("/{agent_id}/extraction")
async def patch_agent_extraction(
    agent_id: int,
    body: ExtractionUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = (await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id)
    )).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    cfg = dict(agent.tools_config or {})
    sub = dict(cfg.get("extraction") or {})

    if body.enabled is not None:
        sub["enabled"] = bool(body.enabled)
    if body.model is not None:
        sub["model"] = body.model or None
    if body.max_facts is not None:
        if not (1 <= body.max_facts <= 20):
            raise HTTPException(status_code=400, detail="max_facts must be 1..20")
        sub["max_facts"] = body.max_facts

    cfg["extraction"] = sub
    agent.tools_config = cfg
    flag_modified(agent, "tools_config")
    await db.commit()
    await db.refresh(agent)

    sub = (agent.tools_config or {}).get("extraction") or {}
    return {
        "enabled": bool(sub.get("enabled", False)),
        "model": sub.get("model"),
        "max_facts": sub.get("max_facts"),
    }


@router.get("/{agent_id}/safety/log")
async def get_agent_safety_log(
    agent_id: int,
    check: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = (await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id)
    )).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if check is not None and check not in SAFETY_NAMES:
        raise HTTPException(status_code=400, detail=f"Unknown check: {check}")

    gate_filter = f"safety_{check}" if check else None
    decisions = await gate_log.list_decisions(
        db, user_id=user.id, agent_id=agent_id, gate=gate_filter, limit=limit
    )
    if check is None:
        decisions = [d for d in decisions if str(d.get("gate", "")).startswith("safety_")]
    return decisions


@router.get("/{agent_id}/gates/log")
async def get_agent_gates_log(
    agent_id: int,
    gate: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = (await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id)
    )).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if gate is not None and gate not in GATE_NAMES:
        raise HTTPException(status_code=400, detail=f"Unknown gate: {gate}")

    return await gate_log.list_decisions(
        db, user_id=user.id, agent_id=agent_id, gate=gate, limit=limit
    )


@router.get("/{agent_id}/activity")
async def get_agent_activity(
    agent_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = (
        await db.execute(select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id))
    ).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # 1. Incoming tasks (agent_messages)
    tasks_res = await db.execute(
        select(AgentMessage)
        .where(AgentMessage.to_agent_id == agent_id, AgentMessage.user_id == user.id)
        .order_by(AgentMessage.created_at.desc())
        .limit(50)
    )
    tasks = tasks_res.scalars().all()

    # 2. Actions taken by agent (activities)
    actions_res = await db.execute(
        select(Activity)
        .where(Activity.agent_id == agent_id, Activity.user_id == user.id)
        .order_by(Activity.created_at.desc())
        .limit(50)
    )
    actions = actions_res.scalars().all()

    # 3. Gate decisions (from MongoDB)
    gate_decisions = await gate_log.list_decisions(db, user_id=user.id, agent_id=agent_id, limit=50)

    # 4. Agent triggers (where agent_id is in agent_ids JSON)
    # Using a simple check: if agent_id is in the list. PostgreSQL JSONB supports this with @> or just fetching and filtering
    # For now, let's fetch recent triggers for the user and filter in Python to be safe with different DB backends
    triggers_res = await db.execute(
        select(AgentTrigger)
        .where(AgentTrigger.user_id == user.id)
        .where(AgentTrigger.last_fired_at.is_not(None))
        .order_by(AgentTrigger.last_fired_at.desc())
        .limit(50)
    )
    all_triggers = triggers_res.scalars().all()
    agent_triggers = [t for t in all_triggers if agent_id in (t.agent_ids or [])]

    events = []

    # Format Tasks
    for t in tasks:
        events.append({
            "id": f"task_{t.id}",
            "type": "task",
            "title": "Incoming Task",
            "status": t.status,
            "timestamp": t.created_at,
            "content": t.task,
            "meta": {"from_agent_id": t.from_agent_id, "result": t.result}
        })

    # Format Actions
    for a in actions:
        events.append({
            "id": f"action_{a.id}",
            "type": "action",
            "title": a.type.replace("_", " ").title(),
            "status": "done",
            "timestamp": a.created_at,
            "content": a.content or a.subject or "",
            "meta": {"channel": a.channel}
        })

    # Format Gate Decisions
    for d in gate_decisions:
        events.append({
            "id": f"gate_{d['_id']}",
            "type": "gate",
            "title": f"Gate: {d['gate']}",
            "status": d["decision"],
            "timestamp": d["created_at"],
            "content": d["reason"],
            "meta": {"model": d["model"], "latency": d["latency_ms"]}
        })

    # Format Triggers
    for tr in agent_triggers:
        events.append({
            "id": f"trigger_{tr.id}_{tr.last_fired_at.isoformat()}",
            "type": "trigger",
            "title": f"Trigger: {tr.name}",
            "status": "fired",
            "timestamp": tr.last_fired_at,
            "content": tr.task_template,
            "meta": {"schedule": tr.cron}
        })

    # Sort all by timestamp DESC
    events.sort(key=lambda x: x["timestamp"], reverse=True)

    return events[:100]


@router.get("/{agent_id}/memories")
async def list_agent_memories(
    agent_id: int,
    scope: str = Query(default="both", pattern="^(private|shared|both)$"),
    q: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = (await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id)
    )).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    try:
        return await memory_service.list_memories(
            db, user_id=user.id, agent_id=agent_id, scope=scope, q=q, limit=limit
        )
    except MemoryServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{agent_id}/memories", status_code=201)
async def create_agent_memory(
    agent_id: int,
    body: MemoryCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = (await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id)
    )).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if body.visibility not in ("private", "shared"):
        raise HTTPException(status_code=400, detail="visibility must be private|shared")
    fact = (body.fact or "").strip()
    if not fact:
        raise HTTPException(status_code=400, detail="fact is required")
    try:
        return await memory_service.store_memory(
            db,
            user_id=user.id,
            agent_id=agent_id if body.visibility == "private" else None,
            fact=fact,
            visibility=body.visibility,
            tags=body.tags or [],
        )
    except MemoryServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{agent_id}/memories/{memory_id}", status_code=204)
async def delete_agent_memory(
    agent_id: int,
    memory_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = (await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id)
    )).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    try:
        ok = await memory_service.delete_memory(
            db, user_id=user.id, agent_id=agent_id, memory_id=memory_id
        )
    except MemoryServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="Memory not found")


async def _process_agent_message(message_id: int) -> None:
    """Worker: pick up a pending agent_messages row and run the target agent."""
    async with async_session() as db:
        msg = (await db.execute(select(AgentMessage).where(AgentMessage.id == message_id))).scalar_one_or_none()
        if not msg or msg.status != "pending":
            return

        msg.status = "in_progress"
        await db.commit()

        agent = (await db.execute(select(Agent).where(Agent.id == msg.to_agent_id))).scalar_one_or_none()
        if not agent or not agent.llm_provider_id:
            msg.status = "failed"
            msg.error = "Agent or provider missing"
            msg.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return

        ctx_str = ""
        if msg.context:
            ctx_str = f"\n\nContext:\n{msg.context}"

        try:
            answer = await run_agent(
                db,
                agent,
                [
                    {"role": "system", "content": agent.system_prompt},
                    {"role": "user", "content": f"{msg.task}{ctx_str}"},
                ],
                session_id=msg.parent_session_id,
            )
            msg.result = answer
            msg.status = "done"
        except LLMError as e:
            msg.error = str(e)
            msg.status = "failed"

        msg.completed_at = datetime.now(timezone.utc)

        # Create notification with the result
        from app.models.notification import Notification
        if msg.status == "done":
            notif = Notification(
                user_id=msg.user_id,
                title=f"Agent \"{agent.name}\" completed task",
                body=(msg.result or "")[:200],
                category="trigger",
                link=f"/dashboard/agents/{agent.id}",
            )
        else:
            notif = Notification(
                user_id=msg.user_id,
                title=f"Agent \"{agent.name}\" failed",
                body=(msg.error or "Unknown error")[:200],
                category="system",
                link=f"/dashboard/agents/{agent.id}",
            )
        db.add(notif)

        await db.commit()
