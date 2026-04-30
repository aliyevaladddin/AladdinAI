import httpx

from app.models.messaging_channel import MessagingChannel


async def test_channel_connection(channel: MessagingChannel) -> tuple[bool, str]:
    if channel.type == "telegram":
        return await _test_telegram(channel)
    elif channel.type == "whatsapp":
        return await _test_whatsapp(channel)
    elif channel.type == "sms":
        return True, "SMS (Twilio) — verify in Twilio dashboard"
    return False, f"Unknown channel type: {channel.type}"


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
