# NOTICE: This file is protected under RCF-PL
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent import Agent
from app.models.chat_session import ChatMessage, ChatSession
from app.models.llm_provider import LLMProvider
from app.models.message_feedback import MessageFeedback
from app.models.user import User
from app.schemas.router import (
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ChatSessionResponse,
    FeedbackRequest,
    FeedbackResponse,
)
from app.security import get_current_user
from app.services.agent_runner import run_agent
from app.services.llm_service import LLMError
from app.services import media as media_service
from app.services import media_storage
from app.services import speech
from app.services.tracing import schedule_feedback_update

router = APIRouter(prefix="/chat", tags=["chat"])


# [RCF:PROTECTED]
async def _read_attachment_bytes(
    db: AsyncSession, user_id: int, filename: str
) -> bytes | None:
    """Read attachment bytes by its public `filename` handle, backend-agnostic.

    The frontend round-trips a stable `filename` (UUID.ext) for every
    attachment. ``resolve`` maps it to the per-backend handle (disk path for
    local, GridFS file_id for mongodb) and ``get_bytes`` reads that handle —
    one code path for both backends.
    """
    handle = await media_storage.resolve(db, user_id, filename)
    if not handle:
        return None
    return await media_storage.get_bytes(db, user_id, handle)


# ── Sessions ──────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
@router.get("/sessions", response_model=list[ChatSessionResponse])
# [RCF:PROTECTED]
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


# [RCF:PROTECTED]
@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
# [RCF:PROTECTED]
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


# [RCF:PROTECTED]
@router.delete("/sessions/{session_id}", status_code=204)
# [RCF:PROTECTED]
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


# [RCF:PROTECTED]
@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
# [RCF:PROTECTED]
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


# [RCF:PROTECTED]
@router.post("/messages/{message_id}/feedback", response_model=FeedbackResponse)
# [RCF:PROTECTED]
async def submit_feedback(
    message_id: int,
    body: FeedbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record a human 👍/👎 on an assistant reply — the strong training signal.

    Upserts one row per (message, user); re-clicking flips the value. The
    durable record lives in Postgres; a fire-and-forget task mirrors the label
    onto the Mongo trace so a later fine-tune set prefers human judgment over
    the weak write-time score.
    """
    if body.value not in ("thumbs_up", "thumbs_down"):
        raise HTTPException(status_code=422, detail="value must be thumbs_up or thumbs_down")

    # Ownership: the message must belong to a session owned by this user.
    msg = (await db.execute(
        select(ChatMessage, ChatSession)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .where(ChatMessage.id == message_id, ChatSession.user_id == user.id)
    )).first()
    if msg is None:
        raise HTTPException(status_code=404, detail="Message not found")
    message, session = msg
    if message.role != "assistant":
        raise HTTPException(status_code=422, detail="Can only rate assistant messages")

    # Atomic upsert on Postgres (prod); portable read-then-write elsewhere
    # (SQLite in tests doesn't support the postgres ON CONFLICT dialect).
    if db.bind and db.bind.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = (
            pg_insert(MessageFeedback)
            .values(
                message_id=message_id,
                session_id=session.id,
                user_id=user.id,
                value=body.value,
            )
            .on_conflict_do_update(
                constraint="uq_message_feedback_message_user",
                set_={
                    "value": body.value,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
        )
        await db.execute(stmt)
    else:
        existing = (await db.execute(
            select(MessageFeedback).where(
                MessageFeedback.message_id == message_id,
                MessageFeedback.user_id == user.id,
            )
        )).scalar_one_or_none()
        if existing:
            existing.value = body.value
        else:
            db.add(MessageFeedback(
                message_id=message_id,
                session_id=session.id,
                user_id=user.id,
                value=body.value,
            ))
    await db.commit()

    # Best-effort: strengthen the training doc. Never blocks the response.
    schedule_feedback_update(user_id=user.id, session_id=session.id, value=body.value, message_content=message.content)

    return FeedbackResponse(message_id=message_id, value=body.value)


# ── Media upload / serving ────────────────────────────────────────────────────

ALLOWED_IMAGE_MIMES = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
}
ALLOWED_AUDIO_MIMES = {
    "audio/webm", "audio/ogg", "audio/oga", "audio/mpeg", "audio/mp3",
    "audio/wav", "audio/x-wav", "audio/wave", "audio/mp4", "audio/flac",
}
ALLOWED_DOC_MIMES = {
    "text/plain", "text/markdown", "text/html", "text/csv", "application/json",
    "application/pdf", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel", "application/xml"
}
ALLOWED_UPLOAD_MIMES = ALLOWED_IMAGE_MIMES | ALLOWED_AUDIO_MIMES | ALLOWED_DOC_MIMES
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB, same as Telegram


# [RCF:PROTECTED]
def _kind_for_mime(mime: str) -> str:
    """Classify an upload so the frontend/agent knows how to handle it."""
    if mime in ALLOWED_AUDIO_MIMES or mime.startswith("audio/"):
        return "audio"
    elif mime in ALLOWED_IMAGE_MIMES or mime.startswith("image/"):
        return "image"
    else:
        return "document"


# [RCF:PROTECTED]
@router.post("/upload")
# [RCF:PROTECTED]
async def upload_attachment(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save an uploaded image, audio clip, or document and return its handle. Client then
    passes the returned `filename` back via ChatRequest.attachments.

    The cross-cycle handle is `filename` (UUID.ext): it is returned by both
    storage backends, round-tripped by the frontend, and used by `get_media`
    and the STT path to read the file back. `file_id` (mongodb) / `path`
    (local) are included for completeness but are not load-bearing — nothing
    keys off them after upload."""
    mime = (file.content_type or "").lower()
    if mime not in ALLOWED_UPLOAD_MIMES:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {mime}")
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 20MB)")
    saved = await media_storage.save_bytes(db, user.id, data, mime)
    
    # Run the background task to parse and index the uploaded file's content in vector search
    from app.services.memory import index_file_in_vector_search
    background_tasks.add_task(
        index_file_in_vector_search,
        user_id=user.id,
        filename=saved["filename"],
        mime=saved["mime"],
    )

    return {
        "filename": saved["filename"],
        # Stable per-backend handle: file_id (mongodb) or path (local).
        "file_id": saved.get("file_id", saved.get("path")),
        "mime": saved["mime"],
        "kind": _kind_for_mime(mime),
    }


# [RCF:PROTECTED]
@router.get("/media/{filename}")
# [RCF:PROTECTED]
async def get_media(
    filename: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Serve a previously uploaded attachment by its `filename` handle.

    Works for both storage backends:
      - local: stream the file from disk via FileResponse (path-traversal-safe
        through media.resolve).
      - mongodb: read the bytes from GridFS and return them with the stored
        content-type (there is no file on disk to FileResponse)."""
    handle = await media_storage.resolve(db, user.id, filename)
    if not handle:
        raise HTTPException(status_code=404, detail="File not found")

    # Local backend resolves to an on-disk path → serve it directly.
    p = media_service.resolve(filename)
    if p:
        return FileResponse(str(p))

    # MongoDB backend: no file on disk, stream bytes from GridFS.
    data = await media_storage.get_bytes(db, user.id, handle)
    if data is None:
        raise HTTPException(status_code=404, detail="File not found")
    import mimetypes
    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return Response(content=data, media_type=media_type)


# ── Send message ──────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
@router.post("")
# [RCF:PROTECTED]
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

    # Разделяем вложения на картинки и аудио — у них разная обработка.
    attachments = body.attachments or []
    audio_atts = [a for a in attachments if (a.get("kind") == "audio") or str(a.get("mime", "")).startswith("audio/")]
    image_atts = [a for a in attachments if a not in audio_atts]

    # Голос → текст: если пришло аудио и текст пуст, транскрибируем его и
    # дальше ведём диалог ровно как с текстом (тот же агент, та же сессия).
    effective_message = body.message or ""
    if audio_atts and not effective_message.strip():
        provider = (await db.execute(
            select(LLMProvider).where(LLMProvider.id == agent.llm_provider_id)
        )).scalar_one_or_none()
        clip = audio_atts[0]
        clip_filename = clip.get("filename") or ""
        audio_bytes = await _read_attachment_bytes(db, user.id, clip_filename)
        if provider and audio_bytes:
            try:
                effective_message = await speech.transcribe(
                    provider, audio_bytes, clip.get("mime") or "audio/webm",
                    filename=clip_filename or "audio.webm",
                )
            except LLMError as e:
                import logging
                logging.getLogger(__name__).warning("STT failed: %s", e)
                raise HTTPException(status_code=502, detail=f"Speech-to-text failed: {e}")
        if not effective_message.strip():
            raise HTTPException(status_code=400, detail="Could not transcribe the audio")

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
            title=effective_message[:60] + ("..." if len(effective_message) > 60 else ""),
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

    user_text = effective_message or ""
    if image_atts:
        names = [a.get("filename") for a in image_atts if a.get("filename")]
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
        "inbound_attachments": attachments,
        "outgoing_attachments": outgoing_attachments,
    }

    if body.stream:
        async def event_generator():
            import json
            import asyncio

            queue = asyncio.Queue()

            async def on_step(event):
                await queue.put(event)

            async def run_in_background():
                try:
                    reply = await run_agent(
                        db, agent, messages_payload,
                        session_id=session.id, extras=extras,
                        on_step=on_step,
                    )
                    
                    voice_atts = []
                    if body.voice_reply and reply.strip():
                        prov = (await db.execute(
                            select(LLMProvider).where(LLMProvider.id == agent.llm_provider_id)
                        )).scalar_one_or_none()
                        if prov:
                            try:
                                audio_bytes, audio_mime = await speech.synthesize(prov, reply)
                                saved = await media_storage.save_bytes(db, user.id, audio_bytes, audio_mime)
                                voice_atts.append({
                                    "filename": saved["filename"],
                                    "file_id": saved.get("file_id", saved.get("path")),
                                    "mime": saved["mime"],
                                    "kind": "audio",
                                    "caption": reply[:200],
                                })
                            except LLMError as e:
                                import logging
                                logging.getLogger(__name__).warning("TTS failed, returning text only: %s", e)

                    # Сохраняем оба сообщения в БД
                    now = datetime.now(timezone.utc)
                    db.add(ChatMessage(
                        session_id=session.id, role="user", content=effective_message,
                        attachments=attachments or None, created_at=now,
                    ))
                    assistant_msg = ChatMessage(
                        session_id=session.id, role="assistant", content=reply, model=agent.model,
                        attachments=(outgoing_attachments + voice_atts) or None,
                    )
                    db.add(assistant_msg)
                    session.updated_at = datetime.now(timezone.utc)
                    await db.commit()
                    await db.refresh(assistant_msg)  # id for client-side feedback

                    await queue.put({
                        "type": "done",
                        "response": reply,
                        "agent_name": agent.name,
                        "model": agent.model,
                        "session_id": session.id,
                        "message_id": assistant_msg.id,
                        "attachments": (outgoing_attachments + voice_atts) or None,
                    })
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).exception("Streaming run_agent failed")
                    await queue.put({"type": "error", "message": str(e)})

            task = asyncio.create_task(run_in_background())
            try:
                while True:
                    event = await queue.get()
                    yield json.dumps(event) + "\n"
                    if event["type"] in ("done", "error"):
                        break
            finally:
                if not task.done():
                    task.cancel()

        from fastapi.responses import StreamingResponse
        return StreamingResponse(event_generator(), media_type="text/event-stream")

    try:
        reply = await run_agent(
            db, agent, messages_payload,
            session_id=session.id, extras=extras,
        )
    except LLMError as e:
        import logging
        logging.getLogger(__name__).exception("run_agent failed for agent %s: %s", agent.id, e)
        raise HTTPException(status_code=502, detail=f"LLM request failed: {e}")

    # Текст → голос: озвучиваем ответ агента, если клиент попросил voice_reply.
    # Тот же контракт вложений, что у картинок — фронт играет его через <audio>.
    if body.voice_reply and reply.strip():
        provider = (await db.execute(
            select(LLMProvider).where(LLMProvider.id == agent.llm_provider_id)
        )).scalar_one_or_none()
        if provider:
            try:
                audio_bytes, audio_mime = await speech.synthesize(provider, reply)
                saved = await media_storage.save_bytes(db, user.id, audio_bytes, audio_mime)
                outgoing_attachments.append({
                    "filename": saved["filename"],
                    # Per-backend handle; frontend fetches via /chat/media/{filename}.
                    "file_id": saved.get("file_id", saved.get("path")),
                    "mime": saved["mime"],
                    "kind": "audio",
                    "caption": reply[:200],
                })
            except LLMError as e:
                # Озвучка — не критична: текст уже есть. Логируем и отдаём как есть.
                import logging
                logging.getLogger(__name__).warning("TTS failed, returning text only: %s", e)

    # Сохраняем оба сообщения в БД
    now = datetime.now(timezone.utc)
    db.add(ChatMessage(
        session_id=session.id, role="user", content=effective_message,
        attachments=attachments or None, created_at=now,
    ))
    assistant_msg = ChatMessage(
        session_id=session.id, role="assistant", content=reply, model=agent.model,
        attachments=outgoing_attachments or None,
    )
    db.add(assistant_msg)

    # Обновляем время сессии
    session.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(assistant_msg)  # populate the id so the client can rate it

    return ChatResponse(
        response=reply,
        agent_name=agent.name,
        model=agent.model,
        session_id=session.id,
        message_id=assistant_msg.id,
        attachments=outgoing_attachments or None,
    )

