"""Agent turn trace-capture.

After (or instead of) an agent reply, persist a rich record of the turn into
the user's own MongoDB (`agent_traces` collection). These traces are the raw
material for a later fine-tuning dataset and for offline evals: input messages,
the tool calls the model chose, and an `outcome` signal.

Config lives in `agent.tools_config.tracing`:

    {
      "tracing": {
        "enabled": true,          # overrides the edition default (see below)
        "redact_pii": false       # reserved (no-op for now), see PII note below
      }
    }

Default state: decided by the open-core edition (`settings.edition`). The
community self-hosted image keeps capture OFF (a community user has no reason
to carry forging instrumentation); internal/cloud editions default ON. A
per-agent `enabled` flag always overrides the edition default, and the
`TRACING_DISABLED` env var is a global kill-switch on top of both. When on,
traces live in the user's *own* Atlas cluster — no vendor exfiltration.

Failure mode: silent. Capture is fire-and-forget and must never affect, delay,
or break the user-facing reply. Errors are logged and swallowed. Mirrors the
structure of `app.services.extraction`.

PII note: traces store raw text — the same trust boundary as memory writes, and
redaction would hurt training fidelity. A `redact_pii` flag is reserved for a
later pass that would reuse `app.services.safety.safety_pii`; it is a no-op now.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.models.agent import Agent
from app.services.memory import MemoryError as MemSvcError
from app.services.memory import get_mongo_db

log = logging.getLogger(__name__)

TRACE_COLLECTION = "agent_traces"
SCHEMA_VERSION = 1
MAX_TEXT = 8000

# Global kill-switch — disables capture for every agent regardless of config.
TRACING_KILL_SWITCH = os.environ.get("TRACING_DISABLED", "").lower() in (
    "1",
    "true",
    "yes",
    "on",
)

# Per-user idempotent index guard, so we issue create_index at most once per
# user per process. create_index itself is idempotent on the Mongo side; this
# just avoids the extra round-trip on every capture.
_indexed_users: set[int] = set()


def _tracing_cfg(agent: Agent) -> dict[str, Any]:
    cfg = agent.tools_config or {}
    if not isinstance(cfg, dict):
        return {}
    sub = cfg.get("tracing")
    return sub if isinstance(sub, dict) else {}


def _edition_default() -> bool:
    """Default capture state when an agent has no explicit `tracing.enabled`.

    The community self-hosted image keeps capture OFF — there is no reason for
    a community user to carry forging instrumentation. Our own editions
    (internal/cloud) default ON.
    """
    return (settings.edition or "community").lower() != "community"


def _tracing_enabled(agent: Agent) -> bool:
    """Explicit per-agent `tracing.enabled` wins; otherwise edition decides."""
    sub = _tracing_cfg(agent)
    val = sub.get("enabled")
    if isinstance(val, bool):
        return val
    return _edition_default()


def _clip(value: Any) -> Any:
    """Truncate long strings to MAX_TEXT; pass through everything else."""
    if isinstance(value, str) and len(value) > MAX_TEXT:
        return value[:MAX_TEXT]
    return value


def _build_doc(agent: Agent, payload: dict[str, Any], session_id: int | None) -> dict[str, Any]:
    """Assemble the agent_traces document from the loop-collected payload."""
    messages = payload.get("messages") or []
    safe_messages = [
        {"role": m.get("role"), "content": _clip(m.get("content"))}
        for m in messages
        if isinstance(m, dict)
    ]
    tool_calls = payload.get("tool_calls") or []

    return {
        "schema_version": SCHEMA_VERSION,
        "user_id": agent.user_id,
        "agent_id": agent.id,
        "agent_role": payload.get("agent_role"),
        "model": payload.get("model"),
        "provider_type": payload.get("provider_type"),
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc),
        "input_user_text": _clip(payload.get("input_user_text") or ""),
        "messages": safe_messages,
        "tool_calls": tool_calls,
        "iterations": int(payload.get("iterations") or 0),
        "final_text": _clip(payload.get("final_text") or ""),
        "outcome": payload.get("outcome"),
        # cheap quality signals — byproducts of the loop, no extra model calls
        "tool_error_count": int(payload.get("tool_error_count") or 0),
        "hit_max_iterations": bool(payload.get("hit_max_iterations")),
        "had_tools": bool(payload.get("had_tools")),
        # deferred to a later labeling pass
        "quality_label": None,
        "reward": None,
    }


async def _ensure_index(mdb, user_id: int) -> None:
    """Idempotently create the export index for this user's trace collection."""
    if user_id in _indexed_users:
        return
    try:
        await mdb[TRACE_COLLECTION].create_index(
            [("user_id", 1), ("agent_id", 1), ("created_at", -1)]
        )
        _indexed_users.add(user_id)
    except Exception as e:  # noqa: BLE001
        # Non-fatal: capture still works without the index, just slower export.
        log.debug("agent_traces index create failed for user %s: %s", user_id, e)


async def _run_trace_capture(
    agent_id: int,
    user_id: int,
    payload: dict[str, Any],
    session_id: int | None,
) -> None:
    """Body of the background task — owns its own DB session, never raises."""
    try:
        async with async_session() as db:
            agent = (await db.execute(
                select(Agent).where(Agent.id == agent_id)
            )).scalar_one_or_none()
            if agent is None or not _tracing_enabled(agent):
                return

            try:
                mdb = await get_mongo_db(db, user_id)
            except MemSvcError:
                # No Mongo configured for this user — nothing to capture into.
                return

            doc = _build_doc(agent, payload, session_id)
            await _ensure_index(mdb, user_id)
            await mdb[TRACE_COLLECTION].insert_one(doc)
    except Exception as e:  # noqa: BLE001
        log.warning("trace capture failed for agent %s: %s", agent_id, e)


def schedule_trace_capture(
    *,
    agent_id: int,
    user_id: int,
    payload: dict[str, Any],
    session_id: int | None = None,
) -> None:
    """Fire-and-forget trace capture.

    Safe to call from inside a request handler — runs on the event loop and
    swallows any error so the caller's response is never delayed or broken.
    """
    if TRACING_KILL_SWITCH:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(_run_trace_capture(agent_id, user_id, payload, session_id))
