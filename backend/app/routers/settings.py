"""System settings API — per-user configuration for storage backend and other settings."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.security import get_current_user
from app.models.system_settings import SystemSettings
from app.models.user import User

router = APIRouter(prefix="/settings", tags=["settings"])


class SystemSettingsSchema(BaseModel):
    media_storage_backend: str  # "local" or "mongodb"


class SystemSettingsResponse(BaseModel):
    id: int
    user_id: int
    media_storage_backend: str
    created_at: datetime
    updated_at: datetime


@router.get("", response_model=SystemSettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get current user's system settings."""
    result = await db.execute(
        select(SystemSettings).where(SystemSettings.user_id == user.id)
    )
    settings = result.scalars().first()

    # Create default settings if not exists
    if not settings:
        settings = SystemSettings(
            user_id=user.id,
            media_storage_backend="local",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return SystemSettingsResponse(
        id=settings.id,
        user_id=settings.user_id,
        media_storage_backend=settings.media_storage_backend,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


@router.put("", response_model=SystemSettingsResponse)
async def update_settings(
    data: SystemSettingsSchema,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update user's system settings."""
    # Validate media_storage_backend
    if data.media_storage_backend not in ("local", "mongodb"):
        raise HTTPException(
            status_code=400,
            detail="media_storage_backend must be 'local' or 'mongodb'",
        )

    result = await db.execute(
        select(SystemSettings).where(SystemSettings.user_id == user.id)
    )
    settings = result.scalars().first()

    if not settings:
        # Create new settings
        settings = SystemSettings(
            user_id=user.id,
            media_storage_backend=data.media_storage_backend,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(settings)
    else:
        # Update existing
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
