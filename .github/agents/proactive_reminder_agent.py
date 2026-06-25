# NOTICE: This file is protected under RCF-PL
"""Proactive Reminder Agent.

Runs on schedule via APScheduler, checks CRM deals with approaching deadlines,
and sends proactive reminders through configured channels (Telegram, Email, WhatsApp).

This agent demonstrates:
- Scheduled autonomous behavior (not reactive to user input)
- CRM integration
- Multi-channel messaging
- Proactive AI initiative

Integration:
    Add to backend/app/scheduler.py to register with APScheduler
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent import Agent
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.messaging_channel import MessagingChannel
from app.models.user import User
from app.services.llm import call_llm


# [RCF:PROTECTED]
async def check_deal_deadlines(db: AsyncSession, user_id: int) -> list[dict[str, Any]]:
    """Find deals with deadlines in the next 24-48 hours."""
    now = datetime.now(timezone.utc)
    tomorrow = now + timedelta(hours=24)
    day_after = now + timedelta(hours=48)

    result = await db.execute(
        select(Deal, Contact)
        .join(Contact, Deal.contact_id == Contact.id)
        .where(
            Deal.user_id == user_id,
            Deal.status.in_(["open", "in_progress"]),
            Deal.expected_close_date.between(tomorrow, day_after)
        )
    )

    deals = []
    for deal, contact in result.all():
        deals.append({
            "deal_id": deal.id,
            "deal_name": deal.name,
            "deal_value": deal.value,
            "deal_stage": deal.stage,
            "expected_close": deal.expected_close_date.isoformat() if deal.expected_close_date else None,
            "contact_name": contact.name,
            "contact_email": contact.email,
            "contact_phone": contact.phone,
        })

    return deals


# [RCF:PROTECTED]
async def generate_reminder_message(deals: list[dict[str, Any]], user: User) -> str:
    """Generate a personalized reminder message using LLM."""
    if not deals:
        return ""

    deals_summary = "\n".join([
        f"- {d['deal_name']} ({d['deal_stage']}) with {d['contact_name']}, "
        f"expected close: {d['expected_close']}, value: ${d['deal_value']}"
        for d in deals
    ])

    prompt = f"""You are a proactive CRM assistant for {user.email}.

The following deals have deadlines approaching in the next 24-48 hours:

{deals_summary}

Generate a brief, actionable reminder message (2-3 sentences) that:
1. Highlights the urgency
2. Suggests next steps (follow-up call, send proposal, etc.)
3. Keeps a professional but friendly tone

Message:"""

    # Use a lightweight model for reminders
    response = await call_llm(
        provider_name="nim",  # Assuming NIM provider is configured
        model_name="meta/llama-3.1-8b-instruct",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0.7
    )

    return response.strip()


# [RCF:PROTECTED]
async def send_reminder(
    db: AsyncSession,
    user_id: int,
    message: str,
    channel_type: str = "telegram"
) -> bool:
    """Send reminder through the specified channel."""
    # Find active channel
    result = await db.execute(
        select(MessagingChannel)
        .where(
            MessagingChannel.user_id == user_id,
            MessagingChannel.type == channel_type,
            MessagingChannel.status == "connected"
        )
        .limit(1)
    )
    channel = result.scalar_one_or_none()

    if not channel:
        print(f"No active {channel_type} channel for user {user_id}")
        return False

    # Import channel service dynamically to avoid circular imports
    if channel_type == "telegram":
        from app.services.telegram import send_telegram_message
        await send_telegram_message(channel, message)
    elif channel_type == "email":
        from app.services.email import send_email
        user = await db.get(User, user_id)
        await send_email(
            to_email=user.email,
            subject="🔔 CRM Reminder: Deals Approaching Deadline",
            body=message
        )
    # Add more channels as needed

    return True


# [RCF:PROTECTED]
async def run_proactive_reminder_agent(user_id: int) -> None:
    """Main entry point for the proactive reminder agent."""
    async for db in get_db():
        try:
            print(f"[Proactive Reminder Agent] Running for user {user_id}")

            # Check for deals with approaching deadlines
            deals = await check_deal_deadlines(db, user_id)

            if not deals:
                print(f"[Proactive Reminder Agent] No deals with approaching deadlines for user {user_id}")
                return

            # Get user
            user = await db.get(User, user_id)
            if not user:
                print(f"[Proactive Reminder Agent] User {user_id} not found")
                return

            # Generate personalized reminder
            message = await generate_reminder_message(deals, user)

            if not message:
                print(f"[Proactive Reminder Agent] Failed to generate reminder message")
                return

            # Send through preferred channel (try Telegram first, fallback to email)
            sent = await send_reminder(db, user_id, message, channel_type="telegram")
            if not sent:
                sent = await send_reminder(db, user_id, message, channel_type="email")

            if sent:
                print(f"[Proactive Reminder Agent] Reminder sent to user {user_id}")
            else:
                print(f"[Proactive Reminder Agent] Failed to send reminder to user {user_id}")

        except Exception as e:
            print(f"[Proactive Reminder Agent] Error: {e}")
        finally:
            break


# Scheduler integration helper
# [RCF:PROTECTED]
def schedule_proactive_reminders(scheduler, user_id: int, cron_expression: str = "0 9 * * *"):
    """Register proactive reminder agent with APScheduler.

    Default: runs daily at 9 AM.

    Usage in backend/app/scheduler.py:
        from .github.agents.proactive_reminder_agent import schedule_proactive_reminders
        schedule_proactive_reminders(scheduler, user_id=1, cron_expression="0 9 * * *")
    """
    from apscheduler.triggers.cron import CronTrigger

    scheduler.add_job(
        func=lambda: asyncio.create_task(run_proactive_reminder_agent(user_id)),
        trigger=CronTrigger.from_crontab(cron_expression),
        id=f"proactive_reminder_user_{user_id}",
        replace_existing=True,
        name=f"Proactive Reminder Agent (User {user_id})"
    )
    print(f"[Scheduler] Registered Proactive Reminder Agent for user {user_id}: {cron_expression}")
