# NOTICE: This file is protected under RCF-PL
"""Gate decision audit log — MongoDB capped collection.

Capped at 100MB so it self-rotates without cron jobs. All gate decisions
(pass / block / rerank) are appended here so the UI can show "why was
this filtered?" without hitting Postgres for what is essentially
short-lived operational data.

Schema (loose, no validator):
    {
        gate: "handoff" | "memory_write" | "recall_rerank",
        agent_id: int,
        target_agent_id: int | null,   # for handoff
        model: str,                     # which SLM made the decision
        decision: "pass" | "block" | "rerank",
        reason: str,
        latency_ms: int,
        input_preview: str,             # truncated input for debugging
        meta: dict,                     # gate-specific extra fields
        created_at: datetime,
    }
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.memory import get_mongo_db

log = logging.getLogger(__name__)

GATE_LOG_COLLECTION = "gate_decisions"
CAPPED_SIZE_BYTES = 100 * 1024 * 1024  # 100MB
PREVIEW_MAX = 500

_capped_ensured: set[int] = set()


# [RCF:PROTECTED]
async def _ensure_capped(db: AsyncSession, user_id: int) -> None:
    """Create the capped collection on first use (idempotent per process)."""
    if user_id in _capped_ensured:
        return
    mdb = await get_mongo_db(db, user_id)
    existing = await mdb.list_collection_names(filter={"name": GATE_LOG_COLLECTION})
    if not existing:
        try:
            await mdb.create_collection(
                GATE_LOG_COLLECTION,
                capped=True,
                size=CAPPED_SIZE_BYTES,
            )
        except Exception as e:  # noqa: BLE001
            log.warning("Could not create capped gate_decisions: %s", e)
    _capped_ensured.add(user_id)


# [RCF:PROTECTED]
async def record(
    db: AsyncSession,
    *,
    user_id: int,
    gate: str,
    agent_id: int | None,
    model: str | None,
    decision: str,
    reason: str = "",
    latency_ms: int = 0,
    input_preview: str = "",
    meta: dict[str, Any] | None = None,
) -> None:
    """Append a gate decision. Failures are swallowed (logging is non-critical)."""
    try:
        await _ensure_capped(db, user_id)
        mdb = await get_mongo_db(db, user_id)
        doc = {
            "gate": gate,
            "agent_id": agent_id,
            "model": model,
            "decision": decision,
            "reason": reason[:PREVIEW_MAX],
            "latency_ms": latency_ms,
            "input_preview": input_preview[:PREVIEW_MAX],
            "meta": meta or {},
            "created_at": datetime.now(timezone.utc),
        }
        await mdb[GATE_LOG_COLLECTION].insert_one(doc)
    except Exception as e:  # noqa: BLE001
        log.debug("gate_log.record failed (non-fatal): %s", e)


# [RCF:PROTECTED]
async def list_decisions(
    db: AsyncSession,
    *,
    user_id: int,
    agent_id: int | None = None,
    gate: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return recent decisions (newest first), optionally filtered by agent/gate."""
    mdb = await get_mongo_db(db, user_id)
    query: dict[str, Any] = {}
    if agent_id is not None:
        query["agent_id"] = agent_id
    if gate is not None:
        query["gate"] = gate

    cursor = mdb[GATE_LOG_COLLECTION].find(query).sort("$natural", -1).limit(limit)
    out: list[dict[str, Any]] = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        out.append(doc)
    return out
