from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent import Agent
from app.models.chat_session import ChatMessage, ChatSession
from app.models.user import User
from app.schemas.router import (
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ChatSessionResponse,
)
from app.security import get_current_user
from app.services.agent_runner import run_agent
from app.services.llm_service import LLMError

router = APIRouter(prefix="/chat", tags=["chat"])


# ── Sessions ──────────────────────────────────────────────────────────────────

@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
    )
    sessions = result.scalars().all()
    return [
        ChatSessionResponse(
            id=s.id,
            agent_id=s.agent_id,
            title=s.title,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
        )
        for s in sessions
    ]


@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
async def create_session(
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent_id = body.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")

    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.user_id == user.id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    session = ChatSession(
        user_id=user.id,
        agent_id=agent_id,
        title=body.get("title", f"Chat with {agent.name}"),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return ChatSessionResponse(
        id=session.id,
        agent_id=session.agent_id,
        title=session.title,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
    )


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
    await db.commit()


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
async def get_messages(
    session_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Проверяем что сессия принадлежит пользователю
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Session not found")

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()
    return [
        ChatMessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            model=m.model,
            created_at=m.created_at.isoformat(),
        )
        for m in messages
    ]


# ── Send message ──────────────────────────────────────────────────────────────

@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not body.agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")

    # Загружаем агента
    result = await db.execute(select(Agent).where(Agent.id == body.agent_id, Agent.user_id == user.id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if not agent.llm_provider_id:
        raise HTTPException(status_code=400, detail="Agent has no LLM provider configured")

    # Получаем или создаём сессию
    if body.session_id:
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == body.session_id, ChatSession.user_id == user.id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = ChatSession(
            user_id=user.id,
            agent_id=agent.id,
            title=body.message[:60] + ("..." if len(body.message) > 60 else ""),
        )
        db.add(session)
        await db.flush()  # получаем session.id без commit

    # Загружаем последние 20 сообщений сессии для контекста
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(20)
    )
    history = list(reversed(result.scalars().all()))

    messages_payload = [{"role": "system", "content": agent.system_prompt}]
    for msg in history:
        messages_payload.append({"role": msg.role, "content": msg.content})
    messages_payload.append({"role": "user", "content": body.message})

    try:
        reply = await run_agent(db, agent, messages_payload, session_id=session.id)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {e}")

    # Сохраняем оба сообщения в БД
    now = datetime.now(timezone.utc)
    db.add(ChatMessage(session_id=session.id, role="user", content=body.message, created_at=now))
    db.add(ChatMessage(session_id=session.id, role="assistant", content=reply, model=agent.model))

    # Обновляем время сессии
    session.updated_at = datetime.now(timezone.utc)

    await db.commit()

    return ChatResponse(
        response=reply,
        agent_name=agent.name,
        model=agent.model,
        session_id=session.id,
    )
