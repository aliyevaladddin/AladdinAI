# NOTICE: This file is protected under RCF-PL
"""Reminders and Task Scheduling Tools for AladdinAI.

Allows agents to set future reminders and automated scheduled tasks.
"""
import logging
from datetime import datetime, timezone

from app.models.agent_trigger import AgentTrigger
from app.services import triggers as triggers_service
from app.tools.base import ToolContext, tool

log = logging.getLogger(__name__)


# [RCF:PROTECTED]
@tool(
    name="create_reminder",
    description=(
        "Set a future reminder for the user. Provide the reminder `text` and "
        "scheduled `remind_at` time in ISO format (e.g. '2025-04-25T09:00:00Z')."
    ),
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Reminder text (e.g., 'Pay Yandex Cloud invoice')."},
            "remind_at": {"type": "string", "description": "ISO format datetime string for when to notify."},
        },
        "required": ["text", "remind_at"],
    },
)
# [RCF:PROTECTED]
async def create_reminder(
    ctx: ToolContext,
    text: str,
    remind_at: str,
) -> dict:
    try:
        dt = datetime.fromisoformat(remind_at.replace("Z", "+00:00"))
        cron_expr = f"{dt.minute} {dt.hour} {dt.day} {dt.month} *"
        trig = AgentTrigger(
            user_id=ctx.user_id,
            name=f"Reminder: {text[:40]}",
            schedule_kind="once",
            cron=cron_expr,
            agent_ids=[ctx.agent_id or 1],
            task_template=f"🔔 REMINDER FOR ALADDIN: {text}",
            enabled=True,
            next_fire_at=dt,
        )
        ctx.db.add(trig)
        await ctx.db.flush()

        triggers_service.upsert(trig)

        return {
            "status": "success",
            "reminder_id": trig.id,
            "text": text,
            "scheduled_at": dt.isoformat(),
        }
    except Exception as e:
        log.exception("create_reminder tool failed")
        return {"error": f"Failed to create reminder: {str(e)}"}
