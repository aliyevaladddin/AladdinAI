# NOTICE: This file is protected under RCF-PL
"""Self-Forging endpoints: freeze a golden set, run the base-vs-forged harness.

These close the self-forging loop (layers 2 & 3 — see `app.services.forging`).
They are gated to non-community editions: a community self-hosted user has no
forging pipeline, mirroring how trace *capture* is off for them by default.

All data stays in the user's own Mongo cluster.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.llm_provider import LLMProvider
from app.models.user import User
from app.schemas.forging import GoldenFreezeRequest, GoldenFreezeResponse, HarnessRequest, HarnessResponse
from app.security import get_current_user
from app.services.forging import freeze_golden_set, get_golden_set, run_harness
from app.services.memory import MemoryError as MemSvcError
from app.services.memory import get_mongo_db

router = APIRouter(prefix="/forging", tags=["forging"])


# [RCF:PROTECTED]
def _require_edition() -> None:
    """Forging is an internal/cloud feature — off for the community image."""
    if (settings.edition or "community").lower() == "community":
        raise HTTPException(
            status_code=403,
            detail="Self-Forging is not available in the community edition.",
        )


# [RCF:PROTECTED]
async def _mongo(db: AsyncSession, user_id: int):
    try:
        return await get_mongo_db(db, user_id)
    except MemSvcError:
        raise HTTPException(
            status_code=400,
            detail="No MongoDB cluster configured for this user — connect one first.",
        )


# [RCF:PROTECTED]
async def _provider(db: AsyncSession, user_id: int, provider_id: int) -> LLMProvider:
    provider = (await db.execute(
        select(LLMProvider).where(
            LLMProvider.id == provider_id, LLMProvider.user_id == user_id
        )
    )).scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail=f"LLM provider {provider_id} not found")
    return provider


# ── layer 2: golden set ──────────────────────────────────────────────────────
# [RCF:PROTECTED]
@router.post("/golden-set", response_model=GoldenFreezeResponse)
# [RCF:PROTECTED]
async def freeze_golden(
    body: GoldenFreezeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Freeze eligible labeled traces into the golden set (idempotent)."""
    _require_edition()
    mdb = await _mongo(db, user.id)
    summary = await freeze_golden_set(
        mdb, user.id,
        min_reward=body.min_reward,
        human_only=body.human_only,
        limit=body.limit,
    )
    return summary


# [RCF:PROTECTED]
@router.get("/golden-set", response_model=list[dict])
# [RCF:PROTECTED]
async def list_golden(
    limit: int = 500,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current frozen golden examples."""
    _require_edition()
    mdb = await _mongo(db, user.id)
    golden = await get_golden_set(mdb, user.id, limit=limit)
    # Drop Mongo's _id (ObjectId isn't JSON-serialisable) and normalise.
    for g in golden:
        g.pop("_id", None)
    return golden


# ── layer 3: harness ─────────────────────────────────────────────────────────
# [RCF:PROTECTED]
@router.post("/harness", response_model=HarnessResponse)
# [RCF:PROTECTED]
async def harness(
    body: HarnessRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Replay the golden set through base and forged models; report the delta."""
    _require_edition()
    mdb = await _mongo(db, user.id)
    base_provider = await _provider(db, user.id, body.base_provider_id)
    forged_provider = await _provider(db, user.id, body.forged_provider_id)
    result = await run_harness(
        mdb, user.id,
        base_provider=base_provider,
        base_model=body.base_model,
        forged_provider=forged_provider,
        forged_model=body.forged_model,
        system_prompt=body.system_prompt or "",
        limit=body.limit,
    )
    return result
