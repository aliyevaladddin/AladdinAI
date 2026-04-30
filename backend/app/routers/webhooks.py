from fastapi import APIRouter, BackgroundTasks, Request
from sqlalchemy import select

from app.database import async_session
from app.models.messaging_channel import MessagingChannel

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


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
