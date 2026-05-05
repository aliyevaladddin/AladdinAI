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
from app.models.user import User
from app.schemas.agents import AgentCreate, AgentResponse, AgentUpdate
from app.security import get_current_user
from app.services import gate_log
from app.services.agent_runner import run_agent
from app.services.llm_service import LLMError

GATE_NAMES = {"handoff", "memory_write", "recall_rerank"}
SAFETY_NAMES = {"ingress", "egress", "pii"}


class GatesUpdate(BaseModel):
    default_gate_model: str | None = None
    gates: dict[str, dict[str, Any]] | None = None  # {name: {enabled: bool, model: str|null}}


class SafetyUpdate(BaseModel):
    default_safety_model: str | None = None
    safety_block_response: str | None = None
    safety: dict[str, dict[str, Any]] | None = None

router = APIRouter(prefix="/agents", tags=["agents"])


class InboxRequest(BaseModel):
    task: str
    context: dict | None = None
    parent_session_id: int | None = None


class InboxResponse(BaseModel):
    message_id: int
    status: str


@router.get("", response_model=list[AgentResponse])
async def list_agents(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.user_id == user.id))
    return result.scalars().all()


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
        await db.commit()
