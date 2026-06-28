# NOTICE: This file is protected under RCF-PL
"""System settings API — per-user configuration for storage backend and other settings."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.security import get_current_user
from app.models.system_settings import SystemSettings
from app.models.user import User

router = APIRouter(prefix="/settings", tags=["settings"])


# [RCF:PROTECTED]
class SystemSettingsSchema(BaseModel):
    media_storage_backend: str  # "local" or "mongodb"


# [RCF:PROTECTED]
class SystemSettingsResponse(BaseModel):
    id: int | None  # None when settings have not been persisted yet (defaults)
    user_id: int
    media_storage_backend: str
    created_at: datetime
    updated_at: datetime


DEFAULT_BACKEND = "local"
ALLOWED_BACKENDS = ("local", "mongodb")


# [RCF:PROTECTED]
@router.get("", response_model=SystemSettingsResponse)
# [RCF:PROTECTED]
async def get_settings(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get current user's system settings.

    Read-only: if the user has no row yet, return defaults without
    writing to the database (a GET must not mutate state).
    """
    result = await db.execute(
        select(SystemSettings).where(SystemSettings.user_id == user.id)
    )
    settings = result.scalars().first()

    if not settings:
        now = datetime.now(timezone.utc)
        return SystemSettingsResponse(
            id=None,
            user_id=user.id,
            media_storage_backend=DEFAULT_BACKEND,
            created_at=now,
            updated_at=now,
        )

    return SystemSettingsResponse(
        id=settings.id,
        user_id=settings.user_id,
        media_storage_backend=settings.media_storage_backend,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


# [RCF:PROTECTED]
@router.put("", response_model=SystemSettingsResponse)
# [RCF:PROTECTED]
async def update_settings(
    data: SystemSettingsSchema,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update user's system settings."""
    # Validate media_storage_backend
    if data.media_storage_backend not in ALLOWED_BACKENDS:
        raise HTTPException(
            status_code=400,
            detail=f"media_storage_backend must be one of {ALLOWED_BACKENDS}",
        )

    result = await db.execute(
        select(SystemSettings).where(SystemSettings.user_id == user.id)
    )
    settings = result.scalars().first()

    if settings:
        settings.media_storage_backend = data.media_storage_backend
        settings.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(settings)
    else:
        # Create new settings. The UNIQUE constraint on user_id makes this
        # race-safe: a concurrent insert raises IntegrityError, after which
        # we roll back and update the row the other request created.
        settings = SystemSettings(
            user_id=user.id,
            media_storage_backend=data.media_storage_backend,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(settings)
        try:
            await db.commit()
            await db.refresh(settings)
        except IntegrityError:
            await db.rollback()
            result = await db.execute(
                select(SystemSettings).where(SystemSettings.user_id == user.id)
            )
            settings = result.scalars().one()
            settings.media_storage_backend = data.media_storage_backend
            settings.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(settings)

    return SystemSettingsResponse(
        id=settings.id,
        user_id=settings.user_id,
        media_storage_backend=settings.media_storage_backend,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


# [RCF:PROTECTED]
@router.post("/security-audit")
# [RCF:PROTECTED]
async def security_audit(user: User = Depends(get_current_user)):
    """Run security audit of tools using NVIDIA SkillSpector."""
    import anyio
    from app.services.security_audit import run_tools_audit
    
    result = await anyio.to_thread.run_sync(run_tools_audit)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result

