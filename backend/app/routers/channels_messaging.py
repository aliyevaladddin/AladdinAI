import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.messaging_channel import MessagingChannel
from app.models.user import User
from app.schemas.channels import MessagingChannelCreate, MessagingChannelResponse
from app.security import get_current_user

router = APIRouter(prefix="/channels/messaging", tags=["channels"])


@router.get("", response_model=list[MessagingChannelResponse])
async def list_channels(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MessagingChannel).where(MessagingChannel.user_id == user.id))
    return result.scalars().all()


@router.post("", response_model=MessagingChannelResponse, status_code=201)
async def create_channel(body: MessagingChannelCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    channel = MessagingChannel(
        user_id=user.id,
        type=body.type,
        name=body.name,
        config=body.config,
        agent_id=body.agent_id,
        webhook_secret=secrets.token_urlsafe(32),
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return channel


@router.post("/{channel_id}/test")
async def test_channel(channel_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MessagingChannel).where(MessagingChannel.id == channel_id, MessagingChannel.user_id == user.id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    from app.services.messaging_service import test_channel_connection
    success, message = await test_channel_connection(channel)

    if success:
        channel.status = "connected"
        await db.commit()

    return {"status": "connected" if success else "error", "message": message}


@router.delete("/{channel_id}", status_code=204)
async def delete_channel(channel_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MessagingChannel).where(MessagingChannel.id == channel_id, MessagingChannel.user_id == user.id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    await db.delete(channel)
    await db.commit()
