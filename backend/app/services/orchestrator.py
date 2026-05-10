from sqlalchemy import select

from app.database import async_session
from app.models.agent import Agent
from app.models.messaging_channel import MessagingChannel
from app.services.agent_runner import run_agent
from app.services.crm_service import find_or_create_contact, log_activity
from app.services.llm_service import LLMError
from app.services.messaging_service import (
    parse_sms_message,
    parse_telegram_message,
    parse_whatsapp_message,
    send_sms,
    send_telegram,
    send_whatsapp,
)


async def handle_incoming_message(channel: MessagingChannel, channel_type: str, payload: dict):
    """Main orchestrator: incoming message → find/create contact → agent → reply."""

    if channel_type == "telegram":
        sender_id, sender_name, text = parse_telegram_message(payload)
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

    print(f"[orchestrator] incoming {channel_type}: sender={sender_id} name={sender_name} text={text[:50] if text else ''}")

    if not text or not sender_id:
        print(f"[orchestrator] skipped: text={bool(text)} sender_id={bool(sender_id)}")
        return

    async with async_session() as db:
        contact = await find_or_create_contact(
            db, channel.user_id, sender_id, sender_name, source=channel_type, is_phone=is_phone
        )
        print(f"[orchestrator] contact: id={contact.id} name={contact.name}")

        await log_activity(
            db, channel.user_id, contact.id,
            activity_type="message_in", channel=channel_type, content=text,
        )

        agent = None
        if channel.agent_id:
            result = await db.execute(select(Agent).where(Agent.id == channel.agent_id))
            agent = result.scalar_one_or_none()

        reply = "I received your message. An agent will respond shortly."
        if agent and agent.llm_provider_id:
            print(f"[orchestrator] running agent {agent.name}...")
            reply = await _get_agent_reply(db, agent, text)
        else:
            print(f"[orchestrator] no agent assigned, using default reply")

        print(f"[orchestrator] reply: {reply[:80]}")

        await log_activity(
            db, channel.user_id, contact.id,
            activity_type="message_out", channel=channel_type, content=reply,
        )

        await db.commit()
        await db.refresh(contact)

    # Trigger webhooks for message received
    from app.services.webhook_service import trigger_webhooks
    import asyncio
    
    asyncio.create_task(trigger_webhooks(channel.user_id, "message_received", {
        "contact_id": contact.id,
        "contact_name": contact.name,
        "channel": channel_type,
        "text": text
    }))

    if channel_type == "telegram":
        chat_id = payload.get("message", {}).get("chat", {}).get("id", sender_id)
        print(f"[orchestrator] sending telegram reply to chat_id={chat_id}")
        try:
            await send_telegram(channel, str(chat_id), reply)
            print(f"[orchestrator] telegram reply sent OK")
        except Exception as exc:
            print(f"[orchestrator] telegram send FAILED: {exc}")
    elif channel_type == "whatsapp":
        await send_whatsapp(channel, sender_id, reply)
    elif channel_type == "whatsapp_waha":
        from app.services.messaging_service import send_waha
        await send_waha(channel, sender_id, reply)
    elif channel_type == "sms":
        await send_sms(channel, sender_id, reply)

    # Trigger webhooks for message sent (reply)
    asyncio.create_task(trigger_webhooks(channel.user_id, "message_sent", {
        "contact_id": contact.id,
        "channel": channel_type,
        "reply": reply
    }))


async def _get_agent_reply(db, agent: Agent, message: str) -> str:
    """Send a single inbound message through the agent's tool-aware runner."""
    try:
        return await run_agent(
            db,
            agent,
            [
                {"role": "system", "content": agent.system_prompt},
                {"role": "user", "content": message},
            ],
        )
    except LLMError as e:
        return f"Agent error: {e}"
