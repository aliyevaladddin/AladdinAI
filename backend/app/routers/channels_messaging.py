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


@router.get("/{channel_id}/waha/qr")
async def get_waha_qr(channel_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MessagingChannel).where(MessagingChannel.id == channel_id, MessagingChannel.user_id == user.id))
    channel = result.scalar_one_or_none()
    if not channel or channel.type != "whatsapp_waha":
        raise HTTPException(status_code=404, detail="WAHA channel not found")

    import httpx
    config = channel.config or {}
    waha_url = config.get("waha_url", "http://192.168.101.75:3000").rstrip("/")
    api_key = config.get("waha_api_key", "")
    session_name = config.get("waha_session", "default")

    headers = {}
    if api_key:
        headers["X-Api-Key"] = api_key

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Tell WAHA to generate the QR image
            headers["Accept"] = "image/png"
            qr_resp = await client.get(f"{waha_url}/api/{session_name}/auth/qr", headers=headers)
            
            if qr_resp.status_code == 200:
                import base64
                encoded = base64.b64encode(qr_resp.content).decode("utf-8")
                return {"status": "qr", "image": f"data:image/png;base64,{encoded}"}
            else:
                return {"status": "error", "message": f"QR not available (status {qr_resp.status_code}). Maybe session is already connected?"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
