from fastapi import APIRouter, BackgroundTasks, Request, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session, get_db
from app.models.messaging_channel import MessagingChannel
from app.models.outgoing_webhook import OutgoingWebhook
from app.models.user import User
from app.security import get_current_user
from app.schemas.webhook import OutgoingWebhookCreate, OutgoingWebhookResponse

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# ... (incoming handlers kept below)

@router.get("/outgoing", response_model=list[OutgoingWebhookResponse])
async def list_outgoing_webhooks(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OutgoingWebhook).where(OutgoingWebhook.user_id == user.id))
    return result.scalars().all()

@router.post("/outgoing", response_model=OutgoingWebhookResponse)
async def create_outgoing_webhook(body: OutgoingWebhookCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    webhook = OutgoingWebhook(
        user_id=user.id,
        name=body.name,
        url=body.url,
        secret=body.secret,
        events=body.events,
        is_active=body.is_active
    )
    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)
    return webhook

@router.delete("/outgoing/{webhook_id}", status_code=204)
async def delete_outgoing_webhook(webhook_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OutgoingWebhook).where(OutgoingWebhook.id == webhook_id, OutgoingWebhook.user_id == user.id))
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await db.delete(webhook)
    await db.commit()

# --- Incoming Handlers ---


async def _get_channel(channel_id: int) -> MessagingChannel | None:
    async with async_session() as db:
        result = await db.execute(select(MessagingChannel).where(MessagingChannel.id == channel_id))
        return result.scalar_one_or_none()


@router.post("/telegram/{channel_id}")
async def telegram_webhook(channel_id: int, request: Request, background_tasks: BackgroundTasks):
    channel = await _get_channel(channel_id)
    if not channel or channel.type != "telegram":
        return {"ok": False}

    payload = await request.json()

    from app.services.orchestrator import handle_incoming_message
    background_tasks.add_task(handle_incoming_message, channel, "telegram", payload)

    return {"ok": True}


@router.post("/whatsapp/{channel_id}")
async def whatsapp_webhook(channel_id: int, request: Request, background_tasks: BackgroundTasks):
    channel = await _get_channel(channel_id)
    if not channel or channel.type != "whatsapp":
        return {"status": "ignored"}

    payload = await request.json()

    from app.services.orchestrator import handle_incoming_message
    background_tasks.add_task(handle_incoming_message, channel, "whatsapp", payload)

    return {"status": "ok"}


@router.post("/sms/{channel_id}")
async def sms_webhook(channel_id: int, request: Request, background_tasks: BackgroundTasks):
    channel = await _get_channel(channel_id)
    if not channel or channel.type != "sms":
        return {"status": "ignored"}

    form = await request.form()
    payload = dict(form)

    from app.services.orchestrator import handle_incoming_message
    background_tasks.add_task(handle_incoming_message, channel, "sms", payload)

    return {"status": "ok"}
