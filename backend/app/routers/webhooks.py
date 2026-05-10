import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session, get_db
from app.models.messaging_channel import MessagingChannel
from app.models.outgoing_webhook import OutgoingWebhook
from app.models.user import User
from app.schemas.webhook import OutgoingWebhookCreate, OutgoingWebhookResponse
from app.security import get_current_user

log = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# --- Outgoing webhooks (CRUD) ---

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
        is_active=body.is_active,
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


# --- Incoming webhook signature verification ---

def _verify_telegram(channel: MessagingChannel, request: Request, raw_body: bytes) -> bool:
    """Telegram sets the secret token in the X-Telegram-Bot-Api-Secret-Token header.
    The user must pass this same token to setWebhook(secret_token=...) when registering.
    """
    if not channel.webhook_secret:
        log.warning("telegram channel %s has no webhook_secret — rejecting request", channel.id)
        return False
    sent = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    return hmac.compare_digest(sent, channel.webhook_secret)


def _verify_whatsapp_cloud(channel: MessagingChannel, request: Request, raw_body: bytes) -> bool:
    """Meta WhatsApp Cloud signs the body with HMAC-SHA256 using the App Secret,
    delivered in X-Hub-Signature-256 as `sha256=<hex>`.

    `app_secret` lives in `channel.config["app_secret"]`. `webhook_secret` (the
    challenge token used by GET verification) is a different value stored on
    the channel row.
    """
    app_secret = (channel.config or {}).get("app_secret")
    if not app_secret:
        log.warning("whatsapp channel %s has no app_secret in config — rejecting request", channel.id)
        return False
    sig_header = request.headers.get("X-Hub-Signature-256", "")
    if not sig_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig_header, expected)


def _verify_waha(channel: MessagingChannel, request: Request, raw_body: bytes) -> bool:
    """WAHA optionally signs webhooks with HMAC-SHA512 in X-Webhook-Hmac when
    `webhook.hmac` is configured server-side.

    Self-hosted WAHA is often run on a private network without HMAC. To avoid
    breaking existing setups we accept unsigned requests when the channel has
    no `webhook_secret`, but log a warning each time. Once a secret is set,
    verification becomes strict.
    """
    if not channel.webhook_secret:
        log.warning("waha channel %s has no webhook_secret — accepting unsigned request", channel.id)
        return True
    sig_header = request.headers.get("X-Webhook-Hmac", "")
    if not sig_header:
        return False
    expected = hmac.new(channel.webhook_secret.encode(), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(sig_header, expected)


def _verify_sms(channel: MessagingChannel, request: Request, raw_body: bytes) -> bool:
    """SMS providers vary. For now we require a shared secret in
    X-Aladdin-Webhook-Secret header. Twilio HMAC validation is a TODO.
    """
    if not channel.webhook_secret:
        log.warning("sms channel %s has no webhook_secret — rejecting request", channel.id)
        return False
    sent = request.headers.get("X-Aladdin-Webhook-Secret", "")
    return hmac.compare_digest(sent, channel.webhook_secret)


_VERIFIERS = {
    "telegram": _verify_telegram,
    "whatsapp": _verify_whatsapp_cloud,
    "whatsapp_waha": _verify_waha,
    "sms": _verify_sms,
}


async def _authorize_channel(channel_id: int, expected_type: str, request: Request) -> tuple[MessagingChannel, bytes]:
    """Load the channel, verify the request signature, and return both the
    channel and the raw body. Raises 401/403/404 on any failure.
    """
    async with async_session() as db:
        result = await db.execute(select(MessagingChannel).where(MessagingChannel.id == channel_id))
        channel = result.scalar_one_or_none()

    if not channel or channel.type != expected_type:
        raise HTTPException(status_code=404, detail="Channel not found")

    raw_body = await request.body()
    verifier = _VERIFIERS.get(channel.type)
    if not verifier or not verifier(channel, request, raw_body):
        raise HTTPException(status_code=401, detail="Webhook signature verification failed")

    return channel, raw_body


# --- Incoming handlers ---

@router.post("/telegram/{channel_id}")
async def telegram_webhook(channel_id: int, request: Request, background_tasks: BackgroundTasks):
    channel, raw_body = await _authorize_channel(channel_id, "telegram", request)
    payload = json.loads(raw_body or b"{}")

    from app.services.orchestrator import handle_incoming_message
    background_tasks.add_task(handle_incoming_message, channel, "telegram", payload)
    return {"ok": True}


@router.get("/whatsapp/{channel_id}")
async def verify_whatsapp_webhook(channel_id: int, request: Request):
    """Meta verifies the webhook URL by calling GET with hub.verify_token —
    it must match `channel.webhook_secret`. No fallback: an unconfigured
    channel returns 503 instead of accepting a hardcoded value.
    """
    async with async_session() as db:
        result = await db.execute(select(MessagingChannel).where(MessagingChannel.id == channel_id))
        channel = result.scalar_one_or_none()
    if not channel or channel.type != "whatsapp":
        raise HTTPException(status_code=404, detail="Channel not found")
    if not channel.webhook_secret:
        raise HTTPException(status_code=503, detail="Channel webhook_secret not configured")

    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token and hmac.compare_digest(token, channel.webhook_secret):
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(challenge or "")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp/{channel_id}")
async def whatsapp_webhook(channel_id: int, request: Request, background_tasks: BackgroundTasks):
    channel, raw_body = await _authorize_channel(channel_id, "whatsapp", request)
    payload = json.loads(raw_body or b"{}")

    from app.services.orchestrator import handle_incoming_message
    background_tasks.add_task(handle_incoming_message, channel, "whatsapp", payload)
    return {"status": "ok"}


@router.post("/whatsapp_waha/{channel_id}")
async def waha_webhook(channel_id: int, request: Request, background_tasks: BackgroundTasks):
    channel, raw_body = await _authorize_channel(channel_id, "whatsapp_waha", request)
    payload = json.loads(raw_body or b"{}")

    from app.services.orchestrator import handle_incoming_message
    background_tasks.add_task(handle_incoming_message, channel, "whatsapp_waha", payload)
    return {"status": "ok"}


@router.post("/sms/{channel_id}")
async def sms_webhook(channel_id: int, request: Request, background_tasks: BackgroundTasks):
    channel, _ = await _authorize_channel(channel_id, "sms", request)

    form = await request.form()
    payload = dict(form)

    from app.services.orchestrator import handle_incoming_message
    background_tasks.add_task(handle_incoming_message, channel, "sms", payload)
    return {"status": "ok"}
