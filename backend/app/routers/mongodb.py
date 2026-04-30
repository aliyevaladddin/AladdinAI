from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.mongo_connection import MongoConnection
from app.models.user import User
from app.schemas.connections import MongoCreate, MongoResponse
from app.security import get_current_user

router = APIRouter(prefix="/mongodb", tags=["mongodb"])


@router.get("", response_model=list[MongoResponse])
async def list_mongo(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MongoConnection).where(MongoConnection.user_id == user.id))
    return result.scalars().all()


@router.post("", response_model=MongoResponse, status_code=201)
async def create_mongo(body: MongoCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    conn = MongoConnection(
        user_id=user.id,
        name=body.name,
        connection_string_encrypted=body.connection_string,
        db_name=body.db_name,
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)
    return conn


@router.post("/{conn_id}/test")
async def test_mongo(conn_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MongoConnection).where(MongoConnection.id == conn_id, MongoConnection.user_id == user.id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    # TODO: actual pymongo connection test
    return {"status": "ok", "message": f"MongoDB test for {conn.db_name} — placeholder"}


@router.delete("/{conn_id}", status_code=204)
async def delete_mongo(conn_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MongoConnection).where(MongoConnection.id == conn_id, MongoConnection.user_id == user.id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    await db.delete(conn)
    await db.commit()
