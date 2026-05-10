import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.activity import Activity
from app.models.user import User
from app.schemas.crm import ActivityCreate, ActivityResponse
from app.security import get_current_user

router = APIRouter(prefix="/crm/activities", tags=["crm"])

ATTACHMENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "media", "attachments")


@router.get("", response_model=list[ActivityResponse])
async def list_activities(
    type: str | None = None,
    channel: str | None = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Activity).where(Activity.user_id == user.id)
    if type:
        types = type.split(",")
        q = q.where(Activity.type.in_(types))
    if channel:
        q = q.where(Activity.channel == channel)
    result = await db.execute(q.order_by(Activity.created_at.desc()).limit(limit))
    return result.scalars().all()


@router.post("", response_model=ActivityResponse, status_code=201)
async def create_activity(body: ActivityCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    activity = Activity(user_id=user.id, **body.model_dump())
    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    return activity

from pydantic import BaseModel

class ActivityUpdate(BaseModel):
    contact_id: int | None = None

@router.patch("/{activity_id}", response_model=ActivityResponse)
async def update_activity(
    activity_id: int,
    body: ActivityUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Activity).where(Activity.id == activity_id, Activity.user_id == user.id)
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    if body.contact_id is not None:
        activity.contact_id = body.contact_id
        
    await db.commit()
    await db.refresh(activity)
    return activity

@router.get("/{activity_id}/attachments/{filename}")
async def download_attachment(
    activity_id: int,
    filename: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download or preview an email attachment by activity ID and filename."""
    result = await db.execute(
        select(Activity).where(Activity.id == activity_id, Activity.user_id == user.id)
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Validate filename exists in activity metadata
    attachments = (activity.metadata_json or {}).get("attachments", [])
    meta = next((a for a in attachments if a["filename"] == filename), None)
    if not meta:
        raise HTTPException(status_code=404, detail="Attachment not found")

    file_path = os.path.join(ATTACHMENTS_DIR, str(activity_id), filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=meta.get("content_type", "application/octet-stream"),
    )
