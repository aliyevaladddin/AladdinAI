import asyncio
import logging

from sqlalchemy import select

from app.database import async_session
from app.models.agent import Agent
from app.models.messaging_channel import MessagingChannel
from app.services.agent_runner import run_agent
from app.services.crm_service import find_or_create_contact, log_activity
from app.services.llm_service import LLMError
from app.services.router_resolver import resolve_agent_id
from app.services.messaging_service import (
    parse_sms_message,
    parse_telegram_message,
    parse_whatsapp_message,
    send_sms,
    send_telegram,
    send_whatsapp,
)

log = logging.getLogger(__name__)


def _fire_and_forget(coro, label: str) -> None:
    """Run a coroutine in the background, log any exception it raises.

    Plain `asyncio.create_task(...)` discards exceptions silently — webhook
    delivery failures would just disappear. This wrapper attaches a callback
    so failures land in the log instead.
    """
    task = asyncio.create_task(coro)

    def _on_done(t: asyncio.Task) -> None:
        if t.cancelled():
            return
        exc = t.exception()
        if exc:
            log.exception("background task %s failed: %s", label, exc, exc_info=exc)

    task.add_done_callback(_on_done)


async def handle_incoming_message(channel: MessagingChannel, channel_type: str, payload: dict):
    """Main orchestrator: incoming message → find/create contact → agent → reply."""

    attachments: list[dict] = []
    if channel_type == "telegram":
        sender_id, sender_name, text, attachments = parse_telegram_message(payload)
        is_phone = False
    elif channel_type == "whatsapp":
        sender_id, sender_name, text = parse_whatsapp_message(payload)
        is_phone = True
    elif channel_type == "whatsapp_waha":
        from app.services.messaging_service import parse_waha_message
        sender_id, sender_name, text = parse_waha_message(payload)
        is_phone = True
    elif channel_type == "sms":
        sender_id, sender_name, text = parse_sms_message(payload)
        is_phone = True
    else:
        return

    log.info(
        "orchestrator: incoming %s sender=%s name=%s attachments=%d",
        channel_type, sender_id, sender_name, len(attachments),
    )

    if (not text and not attachments) or not sender_id:
        log.debug("orchestrator: skipped: text=%s sender_id=%s", bool(text), bool(sender_id))
        return

    if attachments and channel_type == "telegram":
        from app.services.media import download_telegram_file
        token = (channel.config or {}).get("bot_token", "")
        downloaded: list[dict] = []
        for att in attachments:
            file_id = att.get("file_id")
            if not file_id or att.get("kind") != "image":
                continue
            saved = await download_telegram_file(token, file_id)
            if saved:
                downloaded.append({**att, **saved})
        attachments = downloaded

    async with async_session() as db:
        contact = await find_or_create_contact(
            db, channel.user_id, sender_id, sender_name, source=channel_type, is_phone=is_phone
        )

        await log_activity(
            db, channel.user_id, contact.id,
            activity_type="message_in", channel=channel_type, content=text,
        )

        # Router rules can override the channel's default agent based on
        # message content. If none matches, fall back to channel.agent_id.
        routed_agent_id = await resolve_agent_id(
            db, channel.user_id, text or "", channel_agent_id=channel.agent_id
        )
        target_agent_id = routed_agent_id if routed_agent_id is not None else channel.agent_id

        agent = None
        if target_agent_id:
            result = await db.execute(select(Agent).where(Agent.id == target_agent_id))
            agent = result.scalar_one_or_none()

        reply = "I received your message. An agent will respond shortly."
        outgoing_attachments: list[dict] = []
        if agent and agent.llm_provider_id:
            log.info("orchestrator: running agent %s", agent.name)
            recipient = sender_id
            if channel_type == "telegram":
                recipient = str(payload.get("message", {}).get("chat", {}).get("id", sender_id))
            extras: dict = {
                "channel_type": channel_type,
                "channel_id": channel.id,
                "recipient": recipient,
                "inbound_attachments": attachments,
                "outgoing_attachments": outgoing_attachments,
            }
            reply = await _get_agent_reply(
                db, agent, text, attachments=attachments, extras=extras,
            )
        else:
            log.debug("orchestrator: no agent assigned, using default reply")

        await log_activity(
            db, channel.user_id, contact.id,
            activity_type="message_out", channel=channel_type, content=reply,
        )

        await db.commit()
        await db.refresh(contact)

    from app.services.webhook_service import trigger_webhooks

    _fire_and_forget(
        trigger_webhooks(channel.user_id, "message_received", {
            "contact_id": contact.id,
            "contact_name": contact.name,
            "channel": channel_type,
            "text": text,
        }),
        "webhook:message_received",
    )

    if channel_type == "telegram":
        chat_id = payload.get("message", {}).get("chat", {}).get("id", sender_id)
        try:
            if reply:
                await send_telegram(channel, str(chat_id), reply)
        except Exception:
            log.exception("orchestrator: telegram send failed for chat_id=%s", chat_id)
        # send_image (via the tool) only queues the file when the channel is
        # web — for messaging channels the tool dispatches inline. Nothing to
        # flush here unless a future channel adopts the queue pattern.
    elif channel_type == "whatsapp":
        await send_whatsapp(channel, sender_id, reply)
    elif channel_type == "whatsapp_waha":
        from app.services.messaging_service import send_waha
        await send_waha(channel, sender_id, reply)
    elif channel_type == "sms":
        await send_sms(channel, sender_id, reply)

    _fire_and_forget(
        trigger_webhooks(channel.user_id, "message_sent", {
            "contact_id": contact.id,
            "channel": channel_type,
            "reply": reply,
        }),
        "webhook:message_sent",
    )


def _attachments_note(attachments: list[dict] | None) -> str:
    """Build a short system-side note listing image filenames the user attached.
    Agents see only the filename — they use `analyze_image` to inspect content
    and `send_image` to reply with one.
    """
    if not attachments:
        return ""
    names = [a.get("filename") for a in attachments if a.get("filename")]
    if not names:
        return ""
    listing = ", ".join(names)
    return (
        f"\n\n[Attached images from the user: {listing}]\n"
        "Use the `analyze_image` tool with one of these filenames to inspect "
        "the photo. Use `send_image` with a filename to reply with a picture."
    )


async def _get_agent_reply(
    db,
    agent: Agent,
    message: str,
    *,
    attachments: list[dict] | None = None,
    extras: dict | None = None,
) -> str:
    """Run the agent's tool-aware loop on a plain-text user message.

    Inbound images are not inlined as multimodal blocks — the agent gets a
    plain text note listing their filenames and decides whether to call the
    `analyze_image` tool. Outbound images are produced by `send_image`,
    which uses `extras` to route to the right channel.
    """
    note = _attachments_note(attachments)
    user_text = (message or "")
    if note:
        user_text = f"{user_text}{note}" if user_text else note.lstrip()

    try:
        return await run_agent(
            db,
            agent,
            [
                {"role": "system", "content": agent.system_prompt},
                {"role": "user", "content": user_text},
            ],
            extras=extras,
        )
    except LLMError as e:
        return f"Agent error: {e}"
