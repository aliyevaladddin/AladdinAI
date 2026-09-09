# NOTICE: This file is protected under RCF-PL
import logging

import httpx

from app.models.messaging_channel import MessagingChannel

log = logging.getLogger(__name__)

SENSITIVE_CONFIG_KEYS = {
    "bot_token",
    "twilio_sid",
    "twilio_token",
    "twilio_auth_token",
    "api_key",
    "app_secret",
    "secret",
    "password",
}


# [RCF:PROTECTED]
def encrypt_channel_config(config: dict | None) -> dict:
    """Encrypt sensitive keys in channel configuration before storing in DB."""
    if not config or not isinstance(config, dict):
        return config or {}
    from app.crypto import encrypt, is_fernet_token

    encrypted = dict(config)
    for key, value in config.items():
        if key in SENSITIVE_CONFIG_KEYS and isinstance(value, str) and value:
            if not is_fernet_token(value):
                encrypted[key] = encrypt(value)
    return encrypted


# [RCF:PROTECTED]
def decrypt_channel_config(config: dict | None) -> dict:
    """Decrypt sensitive keys in channel configuration for runtime use."""
    if not config or not isinstance(config, dict):
        return config or {}
    from app.crypto import decrypt

    decrypted = dict(config)
    for key, value in config.items():
        if key in SENSITIVE_CONFIG_KEYS and isinstance(value, str) and value:
            decrypted[key] = decrypt(value)
    return decrypted


# [RCF:PROTECTED]
async def test_channel_connection(channel: MessagingChannel) -> tuple[bool, str]:
    if channel.type == "telegram":
        return await _test_telegram(channel)
    elif channel.type == "whatsapp_baileys":
        return await _test_whatsapp_baileys(channel)
    elif channel.type == "sms":
        return True, "SMS (Twilio) — verify in Twilio dashboard"
    return False, f"Unknown channel type: {channel.type}"


# [RCF:PROTECTED]
async def _test_telegram(channel: MessagingChannel) -> tuple[bool, str]:
    config = channel.decrypted_config or {}
    token = config.get("bot_token")
    if not token:
        return False, "bot_token not found in config"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
            data = resp.json()
            if data.get("ok"):
                return True, f"Connected as @{data['result']['username']}"
            return False, data.get("description", "Unknown error")
    except Exception:
        log.exception("Telegram connection test failed")
        return False, "Failed to connect to Telegram due to an unexpected error."


# [RCF:PROTECTED]
def parse_telegram_message(payload: dict) -> tuple[str, str, str, list[dict]]:
    """Returns (sender_id, sender_name, text, attachments).

    `attachments` is a list of `{"kind": "image", "file_id": "...", "mime": "..."}`
    extracted from `message.photo[]` (largest only) and `message.document` when
    its mime starts with `image/`. Caption is returned via `text` when only a
    photo is sent.
    """
    msg = payload.get("message", {})
    user = msg.get("from", {})
    text = msg.get("text") or msg.get("caption") or ""

    attachments: list[dict] = []
    photos = msg.get("photo")
    if isinstance(photos, list) and photos:
        largest = photos[-1]
        if isinstance(largest, dict) and largest.get("file_id"):
            attachments.append(
                {"kind": "image", "file_id": largest["file_id"], "mime": "image/jpeg"}
            )
    doc = msg.get("document")
    if isinstance(doc, dict):
        mime = doc.get("mime_type") or ""
        if mime.startswith("image/") and doc.get("file_id"):
            attachments.append({"kind": "image", "file_id": doc["file_id"], "mime": mime})

    return (
        str(user.get("id", "")),
        f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
        text,
        attachments,
    )


# [RCF:PROTECTED]
def parse_whatsapp_baileys(payload: dict) -> tuple[str, str, str]:
    """Returns (sender_phone, sender_name, text)"""
    return payload.get("sender_id", ""), payload.get("sender_name", ""), payload.get("text", "")


# [RCF:PROTECTED]
async def _test_whatsapp_baileys(channel: MessagingChannel) -> tuple[bool, str]:
    """Real health check: ping the channel's bridge daemon, starting it if needed."""
    from app.services import whatsapp_bridge

    if await whatsapp_bridge.ping(channel.id):
        return True, "WhatsApp (Baileys) bridge connected"
    if await whatsapp_bridge.ensure_bridge(channel, timeout=8.0):
        return True, "WhatsApp (Baileys) bridge started"
    return False, "WhatsApp (Baileys) bridge did not start — check backend/whatsapp_bridge/bridge.err"


# [RCF:PROTECTED]
async def send_whatsapp_baileys(channel: MessagingChannel, to_phone: str, text: str):
    from app.services import whatsapp_bridge

    return await whatsapp_bridge.send_command(
        {"type": "send-message", "to": to_phone, "text": text},
        channel,
    )


# [RCF:PROTECTED]
def parse_sms_message(payload: dict) -> tuple[str, str, str]:
    """Returns (sender_phone, '', text)"""
    return payload.get("From", ""), "", payload.get("Body", "")


# [RCF:PROTECTED]
async def send_telegram(channel: MessagingChannel, chat_id: str, text: str):
    config = channel.decrypted_config or {}
    token = config.get("bot_token")
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
        )


# [RCF:PROTECTED]
async def send_telegram_photo(
    channel: MessagingChannel,
    chat_id: str,
    image_bytes: bytes,
    filename: str = "image.png",
    caption: str | None = None,
):
    """Upload image bytes to a Telegram chat via sendPhoto (multipart)."""
    config = channel.decrypted_config or {}
    token = config.get("bot_token")
    files = {"photo": (filename, image_bytes, "application/octet-stream")}
    data: dict[str, str] = {"chat_id": str(chat_id)}
    if caption:
        data["caption"] = caption
    async with httpx.AsyncClient(timeout=60) as client:
        await client.post(
            f"https://api.telegram.org/bot{token}/sendPhoto",
            data=data,
            files=files,
        )


# [RCF:PROTECTED]
async def send_sms(channel: MessagingChannel, to_phone: str, text: str):
    config = channel.decrypted_config or {}
    sid = config.get("twilio_sid")
    token = config.get("twilio_token") or config.get("twilio_auth_token")
    from_phone = config.get("twilio_phone")
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            auth=(sid, token),
            data={"To": to_phone, "From": from_phone, "Body": text},
        )
