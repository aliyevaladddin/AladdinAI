"""Cron-style trigger scheduler.

A single APScheduler instance lives inside the FastAPI process. On startup we
hydrate it from `agent_triggers` (enabled=True). Create/update/delete go through
this module so the scheduler stays in sync with the database.

Each fire calls `_fire_trigger(trigger_id)` which:
  1. Loads the trigger row.
  2. Inserts one `agent_messages` row per `agent_id` (status='pending').
  3. Schedules the existing `_process_agent_message` worker for each.
  4. Updates `last_fired_at` and `next_fire_at`.

Run-now uses the same `_fire_trigger` path so debug behaviour matches scheduled
behaviour exactly.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from croniter import croniter
from sqlalchemy import select

from app.database import async_session
from app.models.agent_message import AgentMessage
from app.models.agent_trigger import AgentTrigger

log = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="UTC")
    return _scheduler


def _job_id(trigger_id: int) -> str:
    return f"trigger_{trigger_id}"


def validate_cron(expr: str) -> None:
    """Raise ValueError if the cron expression is unparseable."""
    if not expr or not isinstance(expr, str):
        raise ValueError("cron expression is required")
    try:
        croniter(expr, datetime.now(timezone.utc))
    except (ValueError, KeyError) as e:
        raise ValueError(f"invalid cron expression: {e}") from e


def next_fire(expr: str, base: datetime | None = None) -> datetime:
    base = base or datetime.now(timezone.utc)
    return croniter(expr, base).get_next(datetime)


async def _fire_trigger(trigger_id: int) -> list[int]:
    """Insert agent_messages for every agent_id; schedule the worker for each.

    Returns the list of message ids created. Safe to call from the scheduler
    or from a manual `Run now` request.
    """
    # Local import avoids circular dependency at module load.
    from app.routers.agents import _process_agent_message

    async with async_session() as db:
        trig = (await db.execute(
            select(AgentTrigger).where(AgentTrigger.id == trigger_id)
        )).scalar_one_or_none()
        if not trig:
            log.warning("trigger %s not found at fire time", trigger_id)
            return []
        if not trig.enabled:
            log.info("trigger %s disabled, skipping fire", trigger_id)
            return []

        agent_ids = [int(x) for x in (trig.agent_ids or []) if isinstance(x, (int, str))]
        if not agent_ids:
            log.warning("trigger %s has no agent_ids, skipping", trigger_id)
            return []

        message_ids: list[int] = []
        for aid in agent_ids:
            msg = AgentMessage(
                user_id=trig.user_id,
                from_agent_id=None,
                to_agent_id=aid,
                parent_session_id=None,
                task=trig.task_template,
                context=trig.context_template,
                status="pending",
            )
            db.add(msg)
            await db.flush()
            message_ids.append(msg.id)

        trig.last_fired_at = datetime.now(timezone.utc)
        try:
            trig.next_fire_at = next_fire(trig.cron)
        except ValueError:
            trig.next_fire_at = None
        await db.commit()

    # Kick the existing worker per message — fire-and-forget so the scheduler
    # job returns immediately and APScheduler doesn't block its event loop.
    for mid in message_ids:
        asyncio.create_task(_process_agent_message(mid))

    return message_ids


def _register_job(trigger: AgentTrigger) -> None:
    sch = get_scheduler()
    sch.add_job(
        _fire_trigger,
        CronTrigger.from_crontab(trigger.cron, timezone="UTC"),
        args=[trigger.id],
        id=_job_id(trigger.id),
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=300,
    )


def _unregister_job(trigger_id: int) -> None:
    sch = get_scheduler()
    job = sch.get_job(_job_id(trigger_id))
    if job:
        sch.remove_job(job.id)


def upsert(trigger: AgentTrigger) -> None:
    """Add/replace the scheduled job for a trigger."""
    if trigger.enabled:
        _register_job(trigger)
    else:
        _unregister_job(trigger.id)


def remove(trigger_id: int) -> None:
    _unregister_job(trigger_id)


async def run_now(trigger_id: int) -> list[int]:
    return await _fire_trigger(trigger_id)


async def hydrate_from_db() -> None:
    """Load enabled triggers from the DB and register them with the scheduler."""
    sch = get_scheduler()
    if not sch.running:
        sch.start()

    async with async_session() as db:
        rows = (await db.execute(
            select(AgentTrigger).where(AgentTrigger.enabled.is_(True))
        )).scalars().all()
        for t in rows:
            try:
                _register_job(t)
            except Exception as e:  # noqa: BLE001
                log.warning("failed to register trigger %s: %s", t.id, e)


async def shutdown() -> None:
    sch = get_scheduler()
    if sch.running:
        sch.shutdown(wait=False)
