# NOTICE: This file is protected under RCF-PL
# [RCF:PROTECTED]
"""Manual trigger endpoint for the daily digest agent."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.security import get_current_user
from app.models.user import User
from app.services.autonomous_bot_scheduler import send_user_daily_digest

router = APIRouter(prefix="/digest", tags=["Digest Agent"])


# [RCF:PROTECTED]
@router.post("/trigger")
# [RCF:PROTECTED]
async def trigger_daily_digest(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger daily digest manually for the authenticated user and send via Telegram/Email."""
    background_tasks.add_task(send_user_daily_digest, db, user)
    return {"status": "success", "message": "Daily digest is being sent to Telegram/Email"}
