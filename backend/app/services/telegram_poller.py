"""Telegram long-polling service.

Runs as an asyncio background task inside the FastAPI process.
On startup it loads all `telegram` channels from `messaging_channels`
and starts polling `getUpdates` for each one.

This avoids the need for a publicly accessible HTTPS webhook URL,
making local development seamless.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from app.database import async_session
from app.models.messaging_channel import MessagingChannel

log = logging.getLogger(__name__)

_tasks: dict[int, asyncio.Task] = {}
_running = False


async def _poll_channel(channel_id: int, bot_token: str) -> None:
    """Long-poll a single Telegram bot via getUpdates.

    Robustness rules:
      * advance `offset` for every update we see — even ones we can't process,
        so a single bad message can never wedge the poller in a loop.
      * one bad update never aborts the batch; log and continue.
      * non-200 / unparseable responses get a backoff, not a crash.
    """
    offset = 0
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"

    log.info("telegram-poll: started polling for channel %s", channel_id)

    while _running:
        try:
            async with httpx.AsyncClient(timeout=35) as client:
                params: dict = {"timeout": 25, "allowed_updates": ["message"]}
                if offset:
                    params["offset"] = offset

                resp = await client.get(url, params=params)
                try:
                    data = resp.json()
                except Exception as exc:
                    log.warning("telegram-poll: non-JSON response for channel %s: %s", channel_id, exc)
                    await asyncio.sleep(5)
                    continue

                if not isinstance(data, dict) or not data.get("ok"):
                    log.warning("telegram-poll: API error for channel %s: %s", channel_id, data)
                    await asyncio.sleep(5)
                    continue

                updates = data.get("result") or []
                if not isinstance(updates, list):
                    log.warning("telegram-poll: unexpected result shape for channel %s", channel_id)
                    await asyncio.sleep(5)
                    continue

                for update in updates:
                    if not isinstance(update, dict):
                        log.warning("telegram-poll: skipping non-dict update on channel %s", channel_id)
                        continue

                    update_id = update.get("update_id")
                    if not isinstance(update_id, int):
                        log.warning("telegram-poll: update without update_id on channel %s: %r", channel_id, update)
                        continue
                    # Advance offset BEFORE processing so a poison message can't loop forever.
                    offset = update_id + 1

                    if "message" not in update:
                        continue

                    try:
                        async with async_session() as db:
                            res = await db.execute(
                                select(MessagingChannel).where(MessagingChannel.id == channel_id)
                            )
                            channel = res.scalar_one_or_none()

                        if not channel:
                            log.info("telegram-poll: channel %s deleted, stopping", channel_id)
                            return

                        from app.services.orchestrator import handle_incoming_message
                        await handle_incoming_message(channel, "telegram", update)
                        log.debug("telegram-poll: processed update %s for channel %s", update_id, channel_id)

                    except Exception:
                        log.exception("telegram-poll: error processing update %s on channel %s", update_id, channel_id)

        except httpx.TimeoutException:
            continue
        except asyncio.CancelledError:
            log.info("telegram-poll: cancelled for channel %s", channel_id)
            return
        except Exception:
            log.exception("telegram-poll: connection error for channel %s", channel_id)
            await asyncio.sleep(5)


async def start() -> None:
    """Load all telegram channels and start a polling task for each."""
    global _running
    _running = True

    async with async_session() as db:
        res = await db.execute(
            select(MessagingChannel).where(
                MessagingChannel.type == "telegram",
                MessagingChannel.status.in_(["connected", "disconnected"]),
            )
        )
        channels = res.scalars().all()

    if not channels:
        log.info("telegram-poll: no telegram channels found, skipping")
        return

    for ch in channels:
        token = (ch.config or {}).get("bot_token")
        if not token:
            log.warning("telegram-poll: channel %s has no bot_token, skipping", ch.id)
            continue

        task = asyncio.create_task(_poll_channel(ch.id, token))
        _tasks[ch.id] = task
        log.info("telegram-poll: registered channel %s (%s)", ch.id, ch.name)

    log.info("telegram-poll: started %d poller(s)", len(_tasks))


async def stop() -> None:
    """Cancel all polling tasks."""
    global _running
    _running = False

    for cid, task in _tasks.items():
        task.cancel()
        log.info("telegram-poll: stopping channel %s", cid)

    if _tasks:
        await asyncio.gather(*_tasks.values(), return_exceptions=True)

    _tasks.clear()
    log.info("telegram-poll: all pollers stopped")


async def add_channel(channel_id: int, bot_token: str) -> None:
    """Dynamically add a new polling task (e.g. after user creates a channel)."""
    if channel_id in _tasks:
        return
    if not _running:
        return
    task = asyncio.create_task(_poll_channel(channel_id, bot_token))
    _tasks[channel_id] = task
    log.info("telegram-poll: added channel %s", channel_id)


async def remove_channel(channel_id: int) -> None:
    """Stop polling for a deleted channel."""
    task = _tasks.pop(channel_id, None)
    if task:
        task.cancel()
        log.info("telegram-poll: removed channel %s", channel_id)
