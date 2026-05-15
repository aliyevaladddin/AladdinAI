from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
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
from app.services import media as media_service

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
            attachments=m.attachments,
            created_at=m.created_at.isoformat(),
        )
        for m in messages
    ]


# ── Media upload / serving ────────────────────────────────────────────────────

ALLOWED_UPLOAD_MIMES = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB, same as Telegram


@router.post("/upload")
async def upload_attachment(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """Save an uploaded image and return its handle. Client then passes the
    returned `filename` back via ChatRequest.attachments."""
    mime = (file.content_type or "").lower()
    if mime not in ALLOWED_UPLOAD_MIMES:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {mime}")
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 20MB)")
    saved = media_service.save_bytes(data, mime)
    return {
        "filename": saved["filename"],
        "path": saved["path"],
        "mime": saved["mime"],
        "kind": "image",
    }


@router.get("/media/{filename}")
async def get_media(filename: str, user: User = Depends(get_current_user)):
    """Serve a previously uploaded attachment. Path-traversal-safe via media.resolve."""
    p = media_service.resolve(filename)
    if not p:
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(p))


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

    user_text = body.message or ""
    if body.attachments:
        names = [a.get("filename") for a in body.attachments if a.get("filename")]
        if names:
            listing = ", ".join(names)
            note = (
                f"\n\n[Attached images from the user: {listing}]\n"
                "Use the `analyze_image` tool with one of these filenames to "
                "inspect the photo. Use `send_image` with a filename to reply "
                "with a picture."
            )
            user_text = f"{user_text}{note}" if user_text else note.lstrip()
    messages_payload.append({"role": "user", "content": user_text})

    outgoing_attachments: list[dict] = []
    extras = {
        "channel_type": "web",
        "inbound_attachments": body.attachments or [],
        "outgoing_attachments": outgoing_attachments,
    }

    try:
        reply = await run_agent(
            db, agent, messages_payload,
            session_id=session.id, extras=extras,
        )
    except LLMError as e:
        import logging
        logging.getLogger(__name__).exception("run_agent failed for agent %s: %s", agent.id, e)
        raise HTTPException(status_code=502, detail=f"LLM request failed: {e}")

    # Сохраняем оба сообщения в БД
    now = datetime.now(timezone.utc)
    db.add(ChatMessage(
        session_id=session.id, role="user", content=body.message,
        attachments=body.attachments, created_at=now,
    ))
    db.add(ChatMessage(
        session_id=session.id, role="assistant", content=reply, model=agent.model,
        attachments=outgoing_attachments or None,
    ))

    # Обновляем время сессии
    session.updated_at = datetime.now(timezone.utc)

    await db.commit()

    return ChatResponse(
        response=reply,
        agent_name=agent.name,
        model=agent.model,
        session_id=session.id,
        attachments=outgoing_attachments or None,
    )
