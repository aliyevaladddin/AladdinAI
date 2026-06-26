# NOTICE: This file is protected under RCF-PL
"""Telegram Commander — admin command processor.

Allows the workspace owner to control agents and triggers directly via
Telegram messages. Only messages from the authorized admin chat ID
(settings.telegram_chat_id) are processed as commands.

Supported commands (both formats work: spaced and underscore):
  /help                                — list all commands
  /status                              — system overview
  /agents                              — list all agents with status
  /agent start <id>   = /agent_start   — start an agent
  /agent stop <id>    = /agent_stop    — stop an agent
  /agent task <id> <text> = /agent_task — send task to agent (reply sent back)
  /agent create <name> | <prompt> = /agent_create
  /agent delete <id>  = /agent_delete  — delete an agent
  /triggers                            — list all triggers
  /trigger fire <id>  = /trigger_fire  — fire immediately
  /trigger on <id>    = /trigger_on    — enable trigger
  /trigger off <id>   = /trigger_off   — disable trigger
  /trigger create <name> | <cron> | <agent_id> | <task> = /trigger_create
  /trigger delete <id> = /trigger_delete
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.agent import Agent
from app.models.agent_message import AgentMessage
from app.models.agent_trigger import AgentTrigger

if TYPE_CHECKING:
    from app.models.messaging_channel import MessagingChannel

log = logging.getLogger(__name__)

# ── emoji helpers ──────────────────────────────────────────────────────────────
_STATUS_EMOJI = {
    "running": "🟢",
    "active":  "🟢",
    "stopped": "🔴",
    "error":   "❌",
    "idle":    "🟡",
}


def _agent_emoji(status: str) -> str:
    return _STATUS_EMOJI.get(status.lower(), "⚪")


# ── main entry point ───────────────────────────────────────────────────────────

# [RCF:PROTECTED]
async def handle_admin_command(
    channel: "MessagingChannel",
    user_id: int,
    text: str,
    chat_id: str | None = None,
) -> str:
    """Parse and execute an admin command. Returns the reply string."""
    text = text.strip()

    # ── Normalise underscore-style commands from Telegram menu ──────────────
    # When the user taps a menu item Telegram fills in e.g. "/agent_start 3".
    # We normalise these to the canonical spaced form "/agent start 3" so that
    # the rest of the dispatcher doesn't need to know about both variants.
    _UNDERSCORE_MAP = {
        "/agent_start":    "/agent start",
        "/agent_stop":     "/agent stop",
        "/agent_task":     "/agent task",
        "/agent_create":   "/agent create",
        "/agent_delete":   "/agent delete",
        "/trigger_fire":   "/trigger fire",
        "/trigger_on":     "/trigger on",
        "/trigger_off":    "/trigger off",
        "/trigger_create": "/trigger create",
        "/trigger_delete": "/trigger delete",
    }
    for underscore, spaced in _UNDERSCORE_MAP.items():
        if text.lower().startswith(underscore):
            rest = text[len(underscore):]
            text = spaced + rest
            break
    # ── End normalisation ───────────────────────────────────────────────────

    # Strip @BotName suffix that Telegram appends in group chats
    parts = text.split(None, 2)  # up to 3 parts: command, sub, rest
    cmd_raw = parts[0] if parts else ""
    if "@" in cmd_raw:
        cmd_raw = cmd_raw.split("@")[0]
        parts[0] = cmd_raw
        text = " ".join(parts)
    cmd = cmd_raw.lower()

    # ── Smart plural alias ─────────────────────────────────────────────────
    # Allow "/agents task 2 ..." as shorthand for "/agent task 2 ..."
    # and "/triggers fire 1" as shorthand for "/trigger fire 1".
    # If the plural form has NO subcommand it still shows the list.
    if cmd == "/agents" and len(parts) >= 2:
        text = "/agent " + " ".join(parts[1:])
        parts = text.split(None, 2)
        cmd = "/agent"
    if cmd == "/triggers" and len(parts) >= 2:
        text = "/trigger " + " ".join(parts[1:])
        parts = text.split(None, 2)
        cmd = "/trigger"
    # ── End smart alias ────────────────────────────────────────────────────

    try:
        if cmd == "/help":
            return _help_text()

        if cmd == "/status":
            return await _cmd_status(user_id)

        if cmd == "/agents":
            return await _cmd_list_agents(user_id)

        if cmd == "/agent":
            return await _cmd_agent(user_id, parts, text, channel=channel, chat_id=chat_id)

        if cmd == "/triggers":
            return await _cmd_list_triggers(user_id)

        if cmd == "/trigger":
            return await _cmd_trigger(user_id, parts, text)

        return "❓ Unknown command. Type /help to see all available commands."
    except Exception as exc:
        log.exception("telegram-commander: error processing command %r", text)
        return f"❌ Command error: {exc}"


# ── /help ──────────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
def _help_text() -> str:
    return (
        "🤖 *AladdinAI Commander* — command reference:\n\n"
        "*Agents:*\n"
        "• `/agents` — list all agents\n"
        "• `/agent start <id>` — start an agent\n"
        "• `/agent stop <id>` — stop an agent\n"
        "• `/agent task <id> <task>` — send a task to an agent\n"
        "• `/agent create <name> | <system prompt>` — create an agent\n"
        "• `/agent delete <id>` — delete an agent\n\n"
        "*Triggers:*\n"
        "• `/triggers` — list all triggers\n"
        "• `/trigger fire <id>` — run a trigger immediately\n"
        "• `/trigger on <id>` — enable a trigger\n"
        "• `/trigger off <id>` — disable a trigger\n"
        "• `/trigger create <name> | <cron> | <agent\\_id> | <task>` — create trigger\n"
        "• `/trigger delete <id>` — delete a trigger\n\n"
        "*System:*\n"
        "• `/status` — overall system status\n"
        "• `/help` — this help message\n\n"
        "_Cron example: `0 9 * * 1-5` (every weekday at 09:00 UTC)_\n\n"
        "_Tip: Both `/agent task 2 ...` and `/agents task 2 ...` work._"
    )


# ── /status ────────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
async def _cmd_status(user_id: int) -> str:
    async with async_session() as db:
        agents = (await db.execute(
            select(Agent).where(Agent.user_id == user_id)
        )).scalars().all()

        triggers = (await db.execute(
            select(AgentTrigger).where(AgentTrigger.user_id == user_id)
        )).scalars().all()

    total_agents = len(agents)
    running = sum(1 for a in agents if a.status in ("running", "active"))
    stopped = total_agents - running
    total_triggers = len(triggers)
    enabled_triggers = sum(1 for t in triggers if t.enabled)
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return (
        f"📊 *AladdinAI System Status*\n"
        f"🕐 {now_utc}\n\n"
        f"🤖 Agents: *{total_agents}* (🟢 {running} running / 🔴 {stopped} stopped)\n"
        f"⚡ Triggers: *{total_triggers}* (✅ {enabled_triggers} enabled)\n"
    )


# ── /agents ────────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
async def _cmd_list_agents(user_id: int) -> str:
    async with async_session() as db:
        agents = (await db.execute(
            select(Agent).where(Agent.user_id == user_id).order_by(Agent.id)
        )).scalars().all()

    if not agents:
        return "🤖 No agents yet. Create one: `/agent create Name | Your system prompt here`"

    lines = ["🤖 *Agent List:*\n"]
    for a in agents:
        emoji = _agent_emoji(a.status)
        lines.append(f"{emoji} `[{a.id}]` *{a.name}* — {a.role or 'no role'} ({a.status})")
    lines.append(f"\n_Total: {len(agents)}_")
    return "\n".join(lines)


# ── /agent <sub> ───────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
async def _cmd_agent(
    user_id: int,
    parts: list[str],
    full_text: str,
    channel: "MessagingChannel | None" = None,
    chat_id: str | None = None,
) -> str:
    if len(parts) < 2:
        return "⚠️ Specify a subcommand: `start | stop | task | create | delete`"

    sub = parts[1].lower()

    if sub == "start":
        return await _agent_start(user_id, parts)

    if sub == "stop":
        return await _agent_stop(user_id, parts)

    if sub == "task":
        return await _agent_task(user_id, parts, full_text, channel=channel, chat_id=chat_id)

    if sub == "create":
        return await _agent_create(user_id, parts, full_text)

    if sub == "delete":
        return await _agent_delete(user_id, parts)

    return f"⚠️ Unknown agent subcommand: `{sub}`"


# [RCF:PROTECTED]
async def _agent_start(user_id: int, parts: list[str]) -> str:
    if len(parts) < 3:
        return "⚠️ Usage: `/agent start <id>`"
    agent_id = _parse_int(parts[2], "agent id")
    if isinstance(agent_id, str):
        return agent_id

    async with async_session() as db:
        agent = await _get_agent(db, agent_id, user_id)
        if isinstance(agent, str):
            return agent
        agent.status = "running"
        await db.commit()
        return f"🟢 Agent *{agent.name}* `[{agent.id}]` is now running."


# [RCF:PROTECTED]
async def _agent_stop(user_id: int, parts: list[str]) -> str:
    if len(parts) < 3:
        return "⚠️ Usage: `/agent stop <id>`"
    agent_id = _parse_int(parts[2], "agent id")
    if isinstance(agent_id, str):
        return agent_id

    async with async_session() as db:
        agent = await _get_agent(db, agent_id, user_id)
        if isinstance(agent, str):
            return agent
        agent.status = "stopped"
        await db.commit()
        return f"🔴 Agent *{agent.name}* `[{agent.id}]` has been stopped."


# [RCF:PROTECTED]
async def _agent_task(
    user_id: int,
    parts: list[str],
    full_text: str,
    channel: "MessagingChannel | None" = None,
    chat_id: str | None = None,
) -> str:
    """Usage: /agent task <id> <task text>

    Sends the task to the agent and — when channel + chat_id are provided —
    forwards the agent's reply back to the same Telegram chat once the
    background worker completes.
    """
    if len(parts) < 3:
        return "⚠️ Usage: `/agent task <id> <task text>`"

    rest = parts[2]
    sub_parts = rest.split(None, 1)
    if len(sub_parts) < 2:
        return "⚠️ Usage: `/agent task <id> <task text>`"

    agent_id = _parse_int(sub_parts[0], "agent id")
    if isinstance(agent_id, str):
        return agent_id
    task_text = sub_parts[1].strip()

    # First verify agent ownership (quick read — separate session).
    async with async_session() as db:
        agent = await _get_agent(db, agent_id, user_id)
        if isinstance(agent, str):
            return agent
        agent_name = agent.name

    # Insert the AgentMessage row. Retry with backoff if SQLite is locked by
    # a concurrent long-running agent session (LLM call in progress).
    from sqlalchemy.exc import OperationalError as _OE
    msg_id: int | None = None
    for attempt in range(5):
        try:
            async with async_session() as db:
                msg = AgentMessage(
                    user_id=user_id,
                    from_agent_id=None,
                    to_agent_id=agent_id,
                    parent_session_id=None,
                    task=task_text,
                    context={"source": "telegram_commander"},
                    status="pending",
                )
                db.add(msg)
                await db.commit()
                await db.refresh(msg)
                msg_id = msg.id
                break
        except _OE as exc:
            err = str(exc).lower()
            if ("locked" in err or "busy" in err) and attempt < 4:
                wait = 2 ** attempt  # 1s, 2s, 4s, 8s
                log.debug(
                    "telegram-commander: DB locked on INSERT, retry %d/5 in %ds",
                    attempt + 1, wait,
                )
                await asyncio.sleep(wait)
            else:
                raise

    if msg_id is None:
        return "❌ Could not create task — database is busy. Please try again in a moment."

    # Process the message and send the result back to Telegram.
    asyncio.create_task(
        _run_and_reply(msg_id, agent_name, channel, chat_id)
    )

    return (
        f"📨 Task sent to *{agent_name}* `[{agent_id}]`\n"
        f"📝 Task: _{task_text[:200]}_\n"
        f"⏳ Working on it — reply will arrive shortly..."
    )


# [RCF:PROTECTED]
async def _run_and_reply(
    msg_id: int,
    agent_name: str,
    channel: "MessagingChannel | None",
    chat_id: str | None,
) -> None:
    """Background task: run the agent message then send the result to Telegram."""
    from app.routers.agents import _process_agent_message
    try:
        await _process_agent_message(msg_id)
    except Exception:
        log.exception("telegram-commander: _process_agent_message(%s) failed", msg_id)

    if not channel or not chat_id:
        return  # no Telegram channel to reply to

    # Read result from DB — poll if still in_progress (LLM may be slow).
    # We wait up to 120 s in 3-second intervals before giving up.
    msg = None
    for attempt in range(40):
        async with async_session() as db:
            msg = (await db.execute(
                select(AgentMessage).where(AgentMessage.id == msg_id)
            )).scalar_one_or_none()

        if msg is None:
            log.warning("telegram-commander: message %s not found in DB", msg_id)
            return

        if msg.status in ("done", "failed"):
            break  # terminal state reached

        # Still running — wait and retry
        log.debug(
            "telegram-commander: msg %s status=%s, polling (attempt %d/40)",
            msg_id, msg.status, attempt + 1,
        )
        await asyncio.sleep(3)
    else:
        # Timed out waiting for agent
        log.warning("telegram-commander: timed out waiting for msg %s", msg_id)

    if msg is None:
        return

    # Safely extract bot_token from channel config (channel may be detached from session)
    try:
        bot_token = (channel.config or {}).get("bot_token", "")
    except Exception:
        bot_token = ""

    if not bot_token:
        log.warning("telegram-commander: no bot_token on channel, cannot send reply")
        return

    if msg.status == "done" and msg.result:
        reply = f"🤖 *{agent_name}* replied:\n\n{msg.result}"
    elif msg.status == "failed":
        reply = (
            f"❌ *{agent_name}* failed to process the task.\n"
            f"Error: `{msg.error or 'unknown error'}`"
        )
    else:
        reply = (
            f"⏳ *{agent_name}* is still working on task `[{msg_id}]`.\n"
            f"Current status: `{msg.status}`"
        )

    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": reply, "parse_mode": "Markdown"},
            )
    except Exception:
        log.exception(
            "telegram-commander: failed to send agent reply to chat_id=%s", chat_id
        )


# [RCF:PROTECTED]
async def _agent_create(user_id: int, parts: list[str], full_text: str) -> str:
    """Usage: /agent create Agent Name | System prompt"""
    prefix = "/agent create "
    body = full_text[len(prefix):].strip() if full_text.lower().startswith(prefix.lower()) else ""

    if "|" not in body:
        return (
            "⚠️ Usage: `/agent create <name> | <system prompt>`\n"
            "Example: `/agent create Sales Bot | You are a helpful sales assistant.`"
        )

    name_part, prompt_part = body.split("|", 1)
    name = name_part.strip()
    system_prompt = prompt_part.strip()

    if not name or not system_prompt:
        return "⚠️ Name and prompt cannot be empty."

    async with async_session() as db:
        existing = (await db.execute(
            select(Agent).where(Agent.name == name, Agent.user_id == user_id)
        )).scalar_one_or_none()
        if existing:
            return f"⚠️ An agent named *{name}* already exists (id: {existing.id})."

        agent = Agent(
            user_id=user_id,
            name=name,
            role="assistant",
            model="gpt-4o-mini",
            system_prompt=system_prompt,
            status="stopped",
        )
        db.add(agent)
        await db.commit()
        await db.refresh(agent)

    return (
        f"✅ Agent created!\n"
        f"🤖 *{agent.name}* `[{agent.id}]`\n"
        f"📝 Prompt: _{system_prompt[:150]}{'...' if len(system_prompt) > 150 else ''}_\n\n"
        f"Start it with: `/agent start {agent.id}`"
    )


# [RCF:PROTECTED]
async def _agent_delete(user_id: int, parts: list[str]) -> str:
    if len(parts) < 3:
        return "⚠️ Usage: `/agent delete <id>`"
    agent_id = _parse_int(parts[2], "agent id")
    if isinstance(agent_id, str):
        return agent_id

    async with async_session() as db:
        agent = await _get_agent(db, agent_id, user_id)
        if isinstance(agent, str):
            return agent
        name = agent.name
        await db.delete(agent)
        await db.commit()

    return f"🗑 Agent *{name}* `[{agent_id}]` has been deleted."


# ── /triggers ──────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
async def _cmd_list_triggers(user_id: int) -> str:
    async with async_session() as db:
        triggers = (await db.execute(
            select(AgentTrigger)
            .where(AgentTrigger.user_id == user_id)
            .order_by(AgentTrigger.id)
        )).scalars().all()

    if not triggers:
        return (
            "⚡ No triggers yet.\n"
            "Create one: `/trigger create Name | 0 9 * * * | <agent_id> | Task`"
        )

    lines = ["⚡ *Trigger List:*\n"]
    for t in triggers:
        status = "✅" if t.enabled else "⏸"
        last = t.last_fired_at.strftime("%d %b %H:%M") if t.last_fired_at else "never"
        nxt = t.next_fire_at.strftime("%d %b %H:%M") if t.next_fire_at else "—"
        agents_str = ", ".join(str(a) for a in (t.agent_ids or []))
        lines.append(
            f"{status} `[{t.id}]` *{t.name}*\n"
            f"   🕐 Cron: `{t.cron}` | Agents: `{agents_str}`\n"
            f"   Last run: {last} | Next: {nxt}"
        )
    lines.append(f"\n_Total: {len(triggers)}_")
    return "\n".join(lines)


# ── /trigger <sub> ─────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
async def _cmd_trigger(user_id: int, parts: list[str], full_text: str) -> str:
    if len(parts) < 2:
        return "⚠️ Specify a subcommand: `fire | on | off | create | delete`"

    sub = parts[1].lower()

    if sub == "fire":
        return await _trigger_fire(user_id, parts)
    if sub == "on":
        return await _trigger_toggle(user_id, parts, enabled=True)
    if sub == "off":
        return await _trigger_toggle(user_id, parts, enabled=False)
    if sub == "create":
        return await _trigger_create(user_id, full_text)
    if sub == "delete":
        return await _trigger_delete(user_id, parts)

    return f"⚠️ Unknown trigger subcommand: `{sub}`"


# [RCF:PROTECTED]
async def _trigger_fire(user_id: int, parts: list[str]) -> str:
    if len(parts) < 3:
        return "⚠️ Usage: `/trigger fire <id>`"
    trigger_id = _parse_int(parts[2], "trigger id")
    if isinstance(trigger_id, str):
        return trigger_id

    async with async_session() as db:
        trig = await _get_trigger(db, trigger_id, user_id)
        if isinstance(trig, str):
            return trig
        name = trig.name
        agent_count = len(trig.agent_ids or [])

    from app.services.triggers import run_now
    msg_ids = await run_now(trigger_id)

    if not msg_ids:
        return (
            f"⚠️ Trigger *{name}* produced no tasks "
            f"(may be disabled or has no agents assigned)."
        )

    return (
        f"🚀 Trigger *{name}* `[{trigger_id}]` fired!\n"
        f"📨 Tasks created: *{len(msg_ids)}* across {agent_count} agent(s)\n"
        f"🔖 Message IDs: `{', '.join(str(m) for m in msg_ids)}`"
    )


# [RCF:PROTECTED]
async def _trigger_toggle(user_id: int, parts: list[str], enabled: bool) -> str:
    if len(parts) < 3:
        action = "on" if enabled else "off"
        return f"⚠️ Usage: `/trigger {action} <id>`"
    trigger_id = _parse_int(parts[2], "trigger id")
    if isinstance(trigger_id, str):
        return trigger_id

    async with async_session() as db:
        trig = await _get_trigger(db, trigger_id, user_id)
        if isinstance(trig, str):
            return trig
        trig.enabled = enabled
        await db.commit()
        await db.refresh(trig)

    from app.services.triggers import upsert
    upsert(trig)

    icon = "✅" if enabled else "⏸"
    state = "enabled" if enabled else "disabled"
    return f"{icon} Trigger *{trig.name}* `[{trigger_id}]` is now {state}."


# [RCF:PROTECTED]
async def _trigger_create(user_id: int, full_text: str) -> str:
    """Usage: /trigger create <name> | <cron> | <agent_id> | <task>"""
    prefix = "/trigger create "
    body = full_text[len(prefix):].strip() if full_text.lower().startswith(prefix.lower()) else ""

    segments = [s.strip() for s in body.split("|")]
    if len(segments) < 4:
        return (
            "⚠️ Usage:\n"
            "`/trigger create <name> | <cron> | <agent_id> | <task>`\n\n"
            "Example:\n"
            "`/trigger create Morning Digest | 0 9 * * 1-5 | 3 | Summarise yesterday's activity`"
        )

    name = segments[0]
    cron_expr = segments[1]
    agent_id_raw = segments[2]
    task_template = "|".join(segments[3:]).strip()

    if not name:
        return "⚠️ Trigger name cannot be empty."

    agent_id = _parse_int(agent_id_raw, "agent id")
    if isinstance(agent_id, str):
        return agent_id

    from app.services.triggers import validate_cron, next_fire, upsert
    try:
        validate_cron(cron_expr)
    except ValueError as e:
        return f"❌ Invalid cron expression: `{cron_expr}`\nError: {e}"

    async with async_session() as db:
        agent = await _get_agent(db, agent_id, user_id)
        if isinstance(agent, str):
            return agent

        nxt = next_fire(cron_expr)
        trig = AgentTrigger(
            user_id=user_id,
            name=name,
            schedule_kind="cron",
            cron=cron_expr,
            agent_ids=[agent_id],
            task_template=task_template,
            enabled=True,
            next_fire_at=nxt,
        )
        db.add(trig)
        await db.commit()
        await db.refresh(trig)

    upsert(trig)

    return (
        f"✅ Trigger created!\n"
        f"⚡ *{name}* `[{trig.id}]`\n"
        f"🕐 Cron: `{cron_expr}`\n"
        f"🤖 Agent: `[{agent_id}]`\n"
        f"📝 Task: _{task_template[:150]}_\n"
        f"📅 Next run: {nxt.strftime('%Y-%m-%d %H:%M UTC')}"
    )


# [RCF:PROTECTED]
async def _trigger_delete(user_id: int, parts: list[str]) -> str:
    if len(parts) < 3:
        return "⚠️ Usage: `/trigger delete <id>`"
    trigger_id = _parse_int(parts[2], "trigger id")
    if isinstance(trigger_id, str):
        return trigger_id

    async with async_session() as db:
        trig = await _get_trigger(db, trigger_id, user_id)
        if isinstance(trig, str):
            return trig
        name = trig.name
        await db.delete(trig)
        await db.commit()

    from app.services.triggers import remove
    remove(trigger_id)

    return f"🗑 Trigger *{name}* `[{trigger_id}]` has been deleted."


# ── helpers ────────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
def _parse_int(value: str, label: str) -> int | str:
    """Parse integer, return error string on failure."""
    try:
        return int(value.strip())
    except (ValueError, AttributeError):
        return f"⚠️ Invalid {label}: `{value}` — expected a number."


# [RCF:PROTECTED]
async def _get_agent(db: AsyncSession, agent_id: int, user_id: int) -> Agent | str:
    """Fetch agent with ownership check. Returns error string if not found."""
    agent = (await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.user_id == user_id)
    )).scalar_one_or_none()
    if not agent:
        return f"❌ Agent `[{agent_id}]` not found or does not belong to you."
    return agent


# [RCF:PROTECTED]
async def _get_trigger(db: AsyncSession, trigger_id: int, user_id: int) -> AgentTrigger | str:
    """Fetch trigger with ownership check. Returns error string if not found."""
    trig = (await db.execute(
        select(AgentTrigger).where(AgentTrigger.id == trigger_id, AgentTrigger.user_id == user_id)
    )).scalar_one_or_none()
    if not trig:
        return f"❌ Trigger `[{trigger_id}]` not found or does not belong to you."
    return trig


# [RCF:PROTECTED]
def is_admin_command(text: str | None) -> bool:
    """Return True if the message looks like an admin slash command."""
    if not text:
        return False
    return text.strip().startswith("/")
