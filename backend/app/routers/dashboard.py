# NOTICE: This file is protected under RCF-PL
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent import Agent
from app.models.agent_message import AgentMessage
from app.models.agent_trigger import AgentTrigger
from app.models.activity import Activity
from app.models.llm_provider import LLMProvider
from app.models.messaging_channel import MessagingChannel
from app.models.email_account import EmailAccount
from app.models.user import User
from app.security import get_current_user
from app.services import memory, gate_log

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# [RCF:PROTECTED]
@router.get("/stats")
# [RCF:PROTECTED]
async def get_dashboard_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)

    # ── 1. Today's messages ─────────────────────────────────────────────────
    # Source: activities table, type=message_in, last 24h
    msgs_q = (
        select(Activity.channel, func.count(Activity.id))
        .where(
            Activity.user_id == user.id,
            Activity.type == "message_in",
            Activity.created_at >= day_ago,
        )
        .group_by(Activity.channel)
    )
    msgs_res = await db.execute(msgs_q)
    messages_breakdown: dict[str, int] = {}
    for channel, count in msgs_res.all():
        key = (channel or "unknown").lower()
        messages_breakdown[key] = messages_breakdown.get(key, 0) + int(count)
    total_messages_24h = sum(messages_breakdown.values())

    # ── 2. Active agents + Top-5 by responses (24h) ─────────────────────────
    # Source: agents table + agent_messages completed in last 24h
    agents_rows = (await db.execute(
        select(Agent).where(Agent.user_id == user.id)
    )).scalars().all()

    # Count completed responses per agent in 24h
    agent_msgs_q = (
        select(AgentMessage.to_agent_id, func.count(AgentMessage.id))
        .where(
            AgentMessage.user_id == user.id,
            AgentMessage.status == "done",
            AgentMessage.created_at >= day_ago,
        )
        .group_by(AgentMessage.to_agent_id)
    )
    agent_msgs_res = await db.execute(agent_msgs_q)
    responses_by_agent: dict[int, int] = {
        int(aid): int(cnt) for aid, cnt in agent_msgs_res.all()
    }

    top_agents = sorted(
        [
            {
                "id": a.id,
                "name": a.name,
                "status": a.status,
                "responses_24h": responses_by_agent.get(a.id, 0),
            }
            for a in agents_rows
        ],
        key=lambda x: x["responses_24h"],
        reverse=True,
    )[:5]

    # ── 3. Trigger fires (24h) ───────────────────────────────────────────────
    # Source: agent_triggers.last_fired_at (updated by scheduler on each fire)
    trigger_fires_q = await db.execute(
        select(func.count(AgentTrigger.id)).where(
            AgentTrigger.user_id == user.id,
            AgentTrigger.last_fired_at >= day_ago,
        )
    )
    trigger_fires_24h = trigger_fires_q.scalar() or 0

    # Also grab the list of recently fired triggers with names for the tooltip
    fired_triggers_rows = (await db.execute(
        select(AgentTrigger)
        .where(
            AgentTrigger.user_id == user.id,
            AgentTrigger.last_fired_at >= day_ago,
        )
        .order_by(AgentTrigger.last_fired_at.desc())
        .limit(5)
    )).scalars().all()
    fired_triggers = [
        {
            "id": t.id,
            "name": t.name,
            "last_fired_at": t.last_fired_at.isoformat() if t.last_fired_at else None,
            "next_fire_at": t.next_fire_at.isoformat() if t.next_fire_at else None,
        }
        for t in fired_triggers_rows
    ]

    # ── 4. Recent shared memory ──────────────────────────────────────────────
    # Source: MongoDB shared_context collection, last 5 docs
    recent_memories: list[dict] = []
    try:
        recent_memories = await memory.list_memories(
            db, user_id=user.id, agent_id=None, scope="shared", limit=5
        )
        # Serialize datetime fields for JSON
        for m in recent_memories:
            if isinstance(m.get("created_at"), datetime):
                m["created_at"] = m["created_at"].isoformat()
    except Exception:
        pass

    # ── 5. Gate decisions (24h) ──────────────────────────────────────────────
    # Source: gate_decisions MongoDB collection, filtered to last 24h
    gate_stats: dict[str, int] = {"pass": 0, "block": 0, "rerank": 0}
    gate_by_type: dict[str, dict[str, int]] = {}  # {gate_name: {decision: count}}
    try:
        # Fetch last 500 to cover 24h window (capped collection has no time index)
        decisions = await gate_log.list_decisions(db, user_id=user.id, limit=500)
        for d in decisions:
            dt = d.get("created_at")
            if isinstance(dt, str):
                try:
                    dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
                except ValueError:
                    continue
            if dt is None or dt < day_ago:
                continue
            decision = d.get("decision", "unknown")
            gate = d.get("gate", "unknown")
            # Overall stats
            gate_stats[decision] = gate_stats.get(decision, 0) + 1
            # Per-gate breakdown
            if gate not in gate_by_type:
                gate_by_type[gate] = {}
            gate_by_type[gate][decision] = gate_by_type[gate].get(decision, 0) + 1
    except Exception:
        pass

    # ── 6. Channels status ───────────────────────────────────────────────────
    # Source: messaging_channels + email_accounts
    msg_ch_q = await db.execute(
        select(MessagingChannel.type, MessagingChannel.status, MessagingChannel.name)
        .where(MessagingChannel.user_id == user.id)
    )
    messaging_channels = [
        {"type": row[0], "status": row[1], "name": row[2]}
        for row in msg_ch_q.all()
    ]
    connected_messaging = sum(1 for c in messaging_channels if c["status"] == "connected")
    error_messaging = sum(1 for c in messaging_channels if c["status"] in ("error", "sync_error"))

    email_ch_q = await db.execute(
        select(EmailAccount.provider, EmailAccount.status, EmailAccount.email)
        .where(EmailAccount.user_id == user.id)
    )
    email_accounts = [
        {"provider": row[0], "status": row[1], "email": row[2]}
        for row in email_ch_q.all()
    ]
    connected_email = sum(1 for e in email_accounts if e["status"] == "connected")
    error_email = sum(1 for e in email_accounts if e["status"] in ("error", "sync_error"))

    # ── Metadata for onboarding ──────────────────────────────────────────────
    providers_count = (await db.execute(
        select(func.count(LLMProvider.id)).where(LLMProvider.user_id == user.id)
    )).scalar() or 0

    total_memories_count = await memory.count_memories(db, user.id)

    # ── Recent global activity feed ──────────────────────────────────────────
    recent_activities_rows = (await db.execute(
        select(Activity)
        .where(Activity.user_id == user.id)
        .order_by(Activity.created_at.desc())
        .limit(10)
    )).scalars().all()

    return {
        "messages_24h": {
            "total": total_messages_24h,
            "breakdown": messages_breakdown,
        },
        "agents": {
            "total": len(agents_rows),
            "top5": top_agents,
        },
        "trigger_fires_24h": {
            "count": trigger_fires_24h,
            "recent": fired_triggers,
        },
        "recent_shared_memory": recent_memories,
        "gate_decisions_24h": {
            "total": sum(gate_stats.values()),
            "pass": gate_stats.get("pass", 0),
            "block": gate_stats.get("block", 0),
            "rerank": gate_stats.get("rerank", 0),
            "by_gate": gate_by_type,
        },
        "channels": {
            "messaging": {
                "total": len(messaging_channels),
                "connected": connected_messaging,
                "errors": error_messaging,
                "list": messaging_channels,
            },
            "email": {
                "total": len(email_accounts),
                "connected": connected_email,
                "errors": error_email,
                "list": email_accounts,
            },
        },
        # ── Meta for onboarding & header ──────────────────────────────────
        "total_providers": providers_count,
        "total_memories": total_memories_count,
        "recent_activities": [
            {
                "id": a.id,
                "type": a.type,
                "channel": a.channel,
                "subject": a.subject,
                "content": (a.content or "")[:200],
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in recent_activities_rows
        ],
        "system_status": "SECURE",
        "protocol": "RCF/2.0.7",
    }
