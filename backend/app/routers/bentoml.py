import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.bentoml_connection import BentoMLConnection
from app.models.user import User
from app.schemas.connections import BentoMLCreate, BentoMLResponse
from app.security import get_current_user

router = APIRouter(prefix="/bentoml", tags=["bentoml"])


@router.get("", response_model=list[BentoMLResponse])
async def list_bentoml(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BentoMLConnection).where(BentoMLConnection.user_id == user.id))
    return result.scalars().all()


@router.post("", response_model=BentoMLResponse, status_code=201)
async def create_bentoml(body: BentoMLCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    conn = BentoMLConnection(
        user_id=user.id,
        name=body.name,
        endpoint_url=body.endpoint_url,
        api_key_encrypted=body.api_key,
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)
    return conn


@router.post("/{conn_id}/test")
async def test_bentoml(conn_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BentoMLConnection).where(BentoMLConnection.id == conn_id, BentoMLConnection.user_id == user.id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    try:
        headers = {}
        if conn.api_key_encrypted:
            headers["Authorization"] = f"Bearer {conn.api_key_encrypted}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{conn.endpoint_url}/healthz", headers=headers)
            resp.raise_for_status()
        return {"status": "connected"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.delete("/{conn_id}", status_code=204)
async def delete_bentoml(conn_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BentoMLConnection).where(BentoMLConnection.id == conn_id, BentoMLConnection.user_id == user.id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    await db.delete(conn)
    await db.commit()
