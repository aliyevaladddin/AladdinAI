from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session, get_db
from app.models.agent import Agent
from app.models.agent_message import AgentMessage
from app.models.user import User
from app.schemas.agents import AgentCreate, AgentResponse, AgentUpdate
from app.security import get_current_user
from app.services.agent_runner import run_agent
from app.services.llm_service import LLMError

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
