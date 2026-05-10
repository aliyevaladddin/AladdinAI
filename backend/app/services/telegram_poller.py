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
    """Long-poll a single Telegram bot via getUpdates."""
    offset = 0
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"

    print(f"[telegram-poll] started polling for channel {channel_id}")

    while _running:
        try:
            async with httpx.AsyncClient(timeout=35) as client:
                params: dict = {"timeout": 25, "allowed_updates": ["message"]}
                if offset:
                    params["offset"] = offset

                resp = await client.get(url, params=params)
                data = resp.json()

                if not data.get("ok"):
                    print(f"[telegram-poll] API error for channel {channel_id}: {data}")
                    await asyncio.sleep(5)
                    continue

                updates = data.get("result", [])
                for update in updates:
                    offset = update["update_id"] + 1

                    # Only process messages (not edited, not callbacks)
                    if "message" not in update:
                        continue

                    payload = update

                    try:
                        # Re-load channel from DB each time to get fresh config/agent_id
                        async with async_session() as db:
                            res = await db.execute(
                                select(MessagingChannel).where(MessagingChannel.id == channel_id)
                            )
                            channel = res.scalar_one_or_none()

                        if not channel:
                            print(f"[telegram-poll] channel {channel_id} deleted, stopping")
                            return

                        from app.services.orchestrator import handle_incoming_message
                        await handle_incoming_message(channel, "telegram", payload)
                        print(f"[telegram-poll] processed update {update['update_id']} for channel {channel_id}")

                    except Exception as exc:
                        print(f"[telegram-poll] error processing update {update['update_id']}: {exc}")

        except httpx.TimeoutException:
            # Long-poll timeout is normal — just retry
            continue
        except asyncio.CancelledError:
            print(f"[telegram-poll] cancelled for channel {channel_id}")
            return
        except Exception as exc:
            print(f"[telegram-poll] connection error for channel {channel_id}: {exc}")
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
        print("[telegram-poll] no telegram channels found, skipping")
        return

    for ch in channels:
        token = (ch.config or {}).get("bot_token")
        if not token:
            print(f"[telegram-poll] channel {ch.id} has no bot_token, skipping")
            continue

        task = asyncio.create_task(_poll_channel(ch.id, token))
        _tasks[ch.id] = task
        print(f"[telegram-poll] registered channel {ch.id} ({ch.name})")

    print(f"[telegram-poll] started {len(_tasks)} poller(s)")


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
