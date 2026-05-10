import certifi
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.mongo_connection import MongoConnection
from app.models.user import User
from app.schemas.connections import MongoCreate, MongoResponse
from app.security import get_current_user
from app.services.memory import invalidate_mongo_client

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

    client = AsyncIOMotorClient(
        conn.connection_string_encrypted,
        serverSelectionTimeoutMS=5000,
        tlsCAFile=certifi.where(),
    )
    try:
        pong = await client[conn.db_name].command("ping")
        if not pong.get("ok"):
            raise RuntimeError("Server returned ok=0")
        collections = await client[conn.db_name].list_collection_names()
    except Exception as e:
        conn.status = "disconnected"
        await db.commit()
        raise HTTPException(status_code=400, detail=f"Connection failed: {e}") from e
    finally:
        client.close()

    conn.status = "connected"
    await db.commit()
    invalidate_mongo_client(user.id)
    return {
        "status": "ok",
        "db": conn.db_name,
        "collections": collections,
        "message": f"Pinged {conn.db_name} successfully",
    }


@router.put("/{conn_id}", response_model=MongoResponse)
async def update_mongo(
    conn_id: int,
    body: MongoCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(MongoConnection).where(MongoConnection.id == conn_id, MongoConnection.user_id == user.id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    conn.name = body.name
    conn.db_name = body.db_name
    if body.connection_string:
        conn.connection_string_encrypted = body.connection_string
        
    await db.commit()
    await db.refresh(conn)
    invalidate_mongo_client(user.id)
    return conn


@router.delete("/{conn_id}", status_code=204)
async def delete_mongo(conn_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MongoConnection).where(MongoConnection.id == conn_id, MongoConnection.user_id == user.id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    await db.delete(conn)
    await db.commit()
    invalidate_mongo_client(user.id)
