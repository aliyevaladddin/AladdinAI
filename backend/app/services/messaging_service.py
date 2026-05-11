import logging

import httpx

from app.models.messaging_channel import MessagingChannel

log = logging.getLogger(__name__)


async def test_channel_connection(channel: MessagingChannel) -> tuple[bool, str]:
    if channel.type == "telegram":
        return await _test_telegram(channel)
    elif channel.type == "whatsapp":
        return await _test_whatsapp(channel)
    elif channel.type == "whatsapp_waha":
        return await _test_waha(channel)
    elif channel.type == "sms":
        return True, "SMS (Twilio) — verify in Twilio dashboard"
    return False, f"Unknown channel type: {channel.type}"

async def _test_waha(channel: MessagingChannel) -> tuple[bool, str]:
    from app.services.url_safety import validate_external_url
    from fastapi import HTTPException

    config = channel.config or {}
    waha_url = (config.get("waha_url") or "").rstrip("/")
    if not waha_url:
        return False, "waha_url not configured for this channel"
    try:
        validate_external_url(waha_url)
    except HTTPException as exc:
        return False, f"waha_url rejected: {exc.detail}"

    api_key = config.get("waha_api_key", "")
    headers = {"Accept": "application/json"}
    if api_key:
        headers["X-Api-Key"] = api_key
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{waha_url}/api/sessions", headers=headers)
            if resp.status_code == 200:
                return True, "WAHA API connected successfully"
            return False, f"WAHA returned status {resp.status_code}"
    except Exception as e:
        return False, f"Failed to connect to WAHA: {str(e)}"


async def _test_telegram(channel: MessagingChannel) -> tuple[bool, str]:
    token = channel.config.get("bot_token")
    if not token:
        return False, "bot_token not found in config"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
            data = resp.json()
            if data.get("ok"):
                return True, f"Connected as @{data['result']['username']}"
            return False, data.get("description", "Unknown error")
    except Exception as e:
        return False, str(e)


async def _test_whatsapp(channel: MessagingChannel) -> tuple[bool, str]:
    token = channel.config.get("access_token")
    phone_id = channel.config.get("phone_number_id")
    if not token or not phone_id:
        return False, "access_token and phone_number_id required"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://graph.facebook.com/v18.0/{phone_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 200:
                return True, "WhatsApp Business connected"
            return False, resp.text
    except Exception as e:
        return False, str(e)


def parse_telegram_message(payload: dict) -> tuple[str, str, str]:
    """Returns (sender_id, sender_name, text)"""
    msg = payload.get("message", {})
    user = msg.get("from", {})
    return (
        str(user.get("id", "")),
        f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
        msg.get("text", ""),
    )


def parse_whatsapp_message(payload: dict) -> tuple[str, str, str]:
    """Returns (sender_phone, sender_name, text)"""
    entry = payload.get("entry", [{}])[0]
    changes = entry.get("changes", [{}])[0]
    value = changes.get("value", {})
    messages = value.get("messages", [])
    if not messages:
        return "", "", ""
    msg = messages[0]
    contacts = value.get("contacts", [{}])
    name = contacts[0].get("profile", {}).get("name", "") if contacts else ""
    return msg.get("from", ""), name, msg.get("text", {}).get("body", "")


def parse_sms_message(payload: dict) -> tuple[str, str, str]:
    """Returns (sender_phone, '', text)"""
    return payload.get("From", ""), "", payload.get("Body", "")


async def send_telegram(channel: MessagingChannel, chat_id: str, text: str):
    token = channel.config.get("bot_token")
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
        )


async def send_whatsapp(channel: MessagingChannel, to_phone: str, text: str):
    token = channel.config.get("access_token")
    phone_id = channel.config.get("phone_number_id")
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"https://graph.facebook.com/v18.0/{phone_id}/messages",
            headers={"Authorization": f"Bearer {token}"},
            json={"messaging_product": "whatsapp", "to": to_phone, "type": "text", "text": {"body": text}},
        )


async def send_sms(channel: MessagingChannel, to_phone: str, text: str):
    sid = channel.config.get("twilio_sid")
    token = channel.config.get("twilio_token")
    from_phone = channel.config.get("twilio_phone")
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            auth=(sid, token),
            data={"To": to_phone, "From": from_phone, "Body": text},
        )

def parse_waha_message(payload: dict):
    """Parse message from WAHA webhook (whatsapp-web.js engine)."""
    # WAHA usually sends { "event": "message", "payload": { "from": "...", "body": "...", "_data": {"notifyName": "..."} } }
    event = payload.get("event")
    if event != "message":
        return None, None, None

    msg_data = payload.get("payload", {})
    sender_id = msg_data.get("from", "")
    text = msg_data.get("body", "")
    
    # Ignore group messages or statuses
    if "@g.us" in sender_id or "status@broadcast" in sender_id:
        return None, None, None

    sender_name = msg_data.get("_data", {}).get("notifyName", "WhatsApp User")
    
    return sender_id, sender_name, text

async def send_waha(channel: MessagingChannel, to: str, text: str):
    """Send message back to WhatsApp via WAHA API."""
    import httpx

    from app.services.url_safety import validate_external_url

    config = channel.config or {}
    waha_url = (config.get("waha_url") or "").rstrip("/")
    if not waha_url:
        raise RuntimeError("waha_url not configured for this channel")
    validate_external_url(waha_url)
    api_key = config.get("waha_api_key", "")
    session_name = config.get("waha_session", "default")
    
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-Api-Key"] = api_key
        
    payload = {
        "chatId": to,
        "text": text,
        "session": session_name
    }
    
    log.info("waha: sending reply to %s via %s/api/sendText", to, waha_url)
    
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(f"{waha_url}/api/sendText", json=payload, headers=headers)
        resp.raise_for_status()

