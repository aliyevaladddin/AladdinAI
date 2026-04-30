from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.activity import Activity
from app.models.user import User
from app.schemas.crm import ActivityCreate, ActivityResponse
from app.security import get_current_user

router = APIRouter(prefix="/crm/activities", tags=["crm"])


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
        q = q.where(Activity.type == type)
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
