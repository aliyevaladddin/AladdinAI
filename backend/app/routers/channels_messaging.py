import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.messaging_channel import MessagingChannel
from app.models.user import User
from app.schemas.channels import MessagingChannelCreate, MessagingChannelResponse
from app.security import get_current_user

log = logging.getLogger(__name__)

router = APIRouter(prefix="/channels/messaging", tags=["channels"])


@router.get("", response_model=list[MessagingChannelResponse])
async def list_channels(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MessagingChannel).where(MessagingChannel.user_id == user.id))
    return result.scalars().all()


@router.post("", response_model=MessagingChannelResponse, status_code=201)
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


@router.post("/{channel_id}/test")
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


@router.delete("/{channel_id}", status_code=204)
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


@router.get("/{channel_id}/webhook-config")
async def get_webhook_config(channel_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Return the webhook URL, secret, and setup instructions for this channel.

    For self-hosted providers like WAHA, the secret must be configured
    on the provider side too — otherwise the channel runs unsigned and
    incoming requests are accepted with a warning. Knowing this is
    essential for production deployments.
    """
    result = await db.execute(
        select(MessagingChannel).where(
            MessagingChannel.id == channel_id, MessagingChannel.user_id == user.id
        )
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    instructions: dict[str, str] = {}
    if channel.type == "whatsapp_waha":
        instructions["signing"] = (
            "WAHA accepts unsigned webhooks by default. To enable HMAC-SHA512 "
            "verification, set `webhooks[].hmac.key` to the secret above in "
            "your WAHA server config (or pass WHATSAPP_HOOK_HMAC=<secret>)."
        )
        instructions["hmac_algorithm"] = "HMAC-SHA512"
        instructions["header"] = "X-Webhook-Hmac"
    elif channel.type == "telegram":
        instructions["signing"] = (
            "Pass `secret_token` (the secret above) when calling Telegram's "
            "setWebhook. Telegram will echo it back in the X-Telegram-Bot-Api-Secret-Token header."
        )
        instructions["header"] = "X-Telegram-Bot-Api-Secret-Token"
    elif channel.type == "whatsapp":
        instructions["signing"] = (
            "WhatsApp Cloud verifies the webhook URL with the secret as `hub.verify_token`. "
            "For signed requests, also set `app_secret` in this channel's config — Meta will "
            "sign payloads with HMAC-SHA256 in X-Hub-Signature-256."
        )
        instructions["verify_token"] = "use the secret as hub.verify_token"

    return {
        "webhook_url": f"/api/webhooks/{channel.type}/{channel.id}",
        "webhook_secret": channel.webhook_secret,
        "is_configured": bool(channel.webhook_secret),
        "instructions": instructions,
    }


@router.get("/{channel_id}/waha/qr")
async def get_waha_qr(channel_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MessagingChannel).where(MessagingChannel.id == channel_id, MessagingChannel.user_id == user.id))
    channel = result.scalar_one_or_none()
    if not channel or channel.type != "whatsapp_waha":
        raise HTTPException(status_code=404, detail="WAHA channel not found")

    import base64
    import httpx

    from app.services.url_safety import validate_external_url

    config = channel.config or {}
    waha_url = (config.get("waha_url") or "").rstrip("/")
    if not waha_url:
        raise HTTPException(status_code=400, detail="waha_url not configured for this channel")
    validate_external_url(waha_url)

    api_key = config.get("waha_api_key", "")
    session_name = config.get("waha_session", "default")

    headers = {"Accept": "image/png"}
    if api_key:
        headers["X-Api-Key"] = api_key

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            qr_resp = await client.get(f"{waha_url}/api/{session_name}/auth/qr", headers=headers)

            if qr_resp.status_code == 200:
                encoded = base64.b64encode(qr_resp.content).decode("utf-8")
                return {"status": "qr", "image": f"data:image/png;base64,{encoded}"}
            return {"status": "error", "message": f"QR not available (status {qr_resp.status_code}). Maybe session is already connected?"}
    except HTTPException:
        raise
    except Exception:
        log.exception("Unexpected error fetching WAHA QR for channel %s", channel_id)
        raise HTTPException(status_code=500, detail="Failed to fetch QR code from WAHA.")
