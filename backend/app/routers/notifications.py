from fastapi import APIRouter, Depends
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.security import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return recent notifications, newest first."""
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "id": n.id,
            "title": n.title,
            "body": n.body,
            "category": n.category,
            "is_read": n.is_read,
            "link": n.link,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in rows
    ]


@router.get("/unread-count")
async def unread_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user.id,
            Notification.is_read.is_(False),
        )
    )
    return {"count": result.scalar() or 0}


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Notification)
        .where(Notification.id == notification_id, Notification.user_id == user.id)
        .values(is_read=True)
    )
    await db.commit()
    return {"ok": True}


@router.post("/read-all")
async def mark_all_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    await db.commit()
    return {"ok": True}
