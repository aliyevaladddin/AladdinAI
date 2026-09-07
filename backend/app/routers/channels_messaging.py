# NOTICE: This file is protected under RCF-PL
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent import Agent
from app.models.messaging_channel import MessagingChannel
from app.models.user import User
from app.schemas.channels import (
    MessagingChannelCreate,
    MessagingChannelResponse,
    MessagingChannelUpdate,
)
from app.security import get_current_user

log = logging.getLogger(__name__)

router = APIRouter(prefix="/channels/messaging", tags=["channels"])


# [RCF:PROTECTED]
@router.get("", response_model=list[MessagingChannelResponse])
# [RCF:PROTECTED]
async def list_channels(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MessagingChannel).where(MessagingChannel.user_id == user.id))
    return result.scalars().all()


# [RCF:PROTECTED]
@router.post("", response_model=MessagingChannelResponse, status_code=201)
# [RCF:PROTECTED]
async def create_channel(body: MessagingChannelCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    channel = MessagingChannel(
        user_id=user.id,
        type=body.type,
        name=body.name,
        config=body.config,
        agent_id=body.agent_id,
        webhook_secret=secrets.token_urlsafe(32),
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return channel


# [RCF:PROTECTED]
@router.patch("/{channel_id}", response_model=MessagingChannelResponse)
# [RCF:PROTECTED]
async def update_channel(
    channel_id: int,
    body: MessagingChannelUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change which agent answers on this channel.

    The agent must belong to the same user — otherwise a tenant could point
    their channel at someone else's agent. Passing agent_id=null detaches the
    channel (it then falls back to the router/default at dispatch time).
    """
    result = await db.execute(
        select(MessagingChannel).where(
            MessagingChannel.id == channel_id,
            MessagingChannel.user_id == user.id,
        )
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if body.agent_id is not None:
        owns = await db.execute(
            select(Agent.id).where(Agent.id == body.agent_id, Agent.user_id == user.id)
        )
        if owns.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Agent not found")

    channel.agent_id = body.agent_id
    await db.commit()
    await db.refresh(channel)
    return channel


# [RCF:PROTECTED]
@router.post("/{channel_id}/test")
# [RCF:PROTECTED]
async def test_channel(channel_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MessagingChannel).where(MessagingChannel.id == channel_id, MessagingChannel.user_id == user.id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    from app.services.messaging_service import test_channel_connection
    success, message = await test_channel_connection(channel)

    if success:
        channel.status = "connected"
        await db.commit()

        if channel.type == "telegram":
            from app.services import telegram_poller
            token = (channel.config or {}).get("bot_token")
            if token:
                await telegram_poller.add_channel(channel.id, token)

    return {"status": "connected" if success else "error", "message": message}


# [RCF:PROTECTED]
@router.delete("/{channel_id}", status_code=204)
# [RCF:PROTECTED]
async def delete_channel(channel_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MessagingChannel).where(MessagingChannel.id == channel_id, MessagingChannel.user_id == user.id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if channel.type == "telegram":
        from app.services import telegram_poller
        await telegram_poller.remove_channel(channel.id)

    await db.delete(channel)
    await db.commit()


# [RCF:PROTECTED]
@router.get("/{channel_id}/webhook-config")
# [RCF:PROTECTED]
async def get_webhook_config(channel_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Return the webhook URL, secret, and setup instructions for this channel."""
    result = await db.execute(
        select(MessagingChannel).where(
            MessagingChannel.id == channel_id, MessagingChannel.user_id == user.id
        )
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    instructions: dict[str, str] = {}
    if channel.type == "telegram":
        instructions["signing"] = (
            "Pass `secret_token` (the secret above) when calling Telegram's "
            "setWebhook. Telegram will echo it back in the X-Telegram-Bot-Api-Secret-Token header."
        )
        instructions["header"] = "X-Telegram-Bot-Api-Secret-Token"
    elif channel.type == "whatsapp_baileys":
        instructions["signing"] = (
            "The internal Baileys bridge signs every webhook post with this "
            "secret in the X-Bridge-Secret header — it binds automatically when "
            "the bridge daemon starts. Nothing to configure by hand."
        )
        instructions["header"] = "X-Bridge-Secret"

    return {
        "webhook_url": f"/api/webhooks/{channel.type}/{channel.id}",
        "webhook_secret": channel.webhook_secret,
        "is_configured": bool(channel.webhook_secret),
        "instructions": instructions,
    }


# [RCF:PROTECTED]
@router.get("/{channel_id}/baileys/qr")
# [RCF:PROTECTED]
async def get_baileys_qr(channel_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MessagingChannel).where(MessagingChannel.id == channel_id, MessagingChannel.user_id == user.id))
    channel = result.scalar_one_or_none()
    if not channel or channel.type != "whatsapp_baileys":
        raise HTTPException(status_code=404, detail="Baileys channel not found")

    from app.services import whatsapp_bridge

    # The daemon signs webhook posts with this secret — make sure the row has
    # one even if it was created before secrets were generated by default.
    if not channel.webhook_secret:
        channel.webhook_secret = secrets.token_urlsafe(32)
        db.add(channel)
        await db.commit()

    await whatsapp_bridge.ensure_bridge(channel)

    qr_res = await whatsapp_bridge.send_command({"type": "get-qr"}, channel)
    if qr_res.get("type") == "qr" and qr_res.get("data"):
        return {"status": "qr", "image": qr_res["data"]}
    return {"status": "error", "message": "QR not ready or already connected"}
