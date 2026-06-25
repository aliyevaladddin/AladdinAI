# NOTICE: This file is protected under RCF-PL
"""Helper to create Proactive Reminder Agent trigger.

Usage:
    from app.services.proactive_reminder_setup import create_proactive_reminder_trigger

    # In a migration or setup script:
    await create_proactive_reminder_trigger(db, user_id=1, agent_id=5)
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_trigger import AgentTrigger
from app.services import triggers as triggers_service


# [RCF:PROTECTED]
async def create_proactive_reminder_trigger(
    db: AsyncSession,
    user_id: int,
    agent_id: int,
    cron: str = "0 9 * * *",  # Daily at 9 AM UTC
) -> AgentTrigger:
    """Create a trigger for the Proactive Reminder Agent.

    Args:
        db: Database session
        user_id: User ID
        agent_id: Agent ID that will handle reminders
        cron: Cron expression (default: daily at 9 AM UTC)

    Returns:
        Created AgentTrigger instance
    """
    trigger = AgentTrigger(
        user_id=user_id,
        name="Daily CRM Reminders",
        description="Proactively checks CRM deals with approaching deadlines and sends reminders",
        cron=cron,
        agent_ids=[agent_id],
        task_template=(
            "Check CRM deals with deadlines in the next 24-48 hours. "
            "For each deal approaching deadline, generate a personalized reminder message "
            "and send it via the contact's preferred channel (Telegram, Email, or WhatsApp). "
            "Include: deal name, contact name, deadline, suggested next steps."
        ),
        context_template=(
            "You are a proactive CRM assistant. Your role is to help users stay on top of "
            "important deals by sending timely reminders. Be concise, actionable, and professional."
        ),
        enabled=True,
        next_fire_at=triggers_service.next_fire(cron),
    )

    db.add(trigger)
    await db.commit()
    await db.refresh(trigger)

    # Register with scheduler
    triggers_service.upsert(trigger)

    return trigger
