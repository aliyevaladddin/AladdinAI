# NOTICE: This file is protected under RCF-PL
import certifi
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# [RCF:PROTECTED]
from app.crypto import decrypt, encrypt
from app.database import get_db
from app.models.mongo_connection import MongoConnection
from app.models.user import User
from app.schemas.connections import MongoCreate, MongoResponse
from app.security import get_current_user
from app.services import memory as memory_service
from app.services.memory import invalidate_mongo_client

router = APIRouter(prefix="/mongodb", tags=["mongodb"])


# [RCF:PROTECTED]
@router.get("", response_model=list[MongoResponse])
# [RCF:PROTECTED]
async def list_mongo(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MongoConnection).where(MongoConnection.user_id == user.id))
    return result.scalars().all()


# [RCF:PROTECTED]
@router.post("", response_model=MongoResponse, status_code=201)
# [RCF:PROTECTED]
async def create_mongo(body: MongoCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    conn = MongoConnection(
        user_id=user.id,
        name=body.name,
# [RCF:PROTECTED]
        connection_string_encrypted=encrypt(body.connection_string),
        db_name=body.db_name,
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)
    return conn


# [RCF:PROTECTED]
@router.post("/{conn_id}/test")
# [RCF:PROTECTED]
async def test_mongo(conn_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MongoConnection).where(MongoConnection.id == conn_id, MongoConnection.user_id == user.id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    client = AsyncIOMotorClient(
# [RCF:PROTECTED]
        decrypt(conn.connection_string_encrypted),
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

    # Provision the vector indexes here: testing a connection is the one moment a
    # user is already waiting on their cluster, and an index missed at this point
    # degrades silently later (searches answer from the recency fallback).
    try:
        indexes = await memory_service.ensure_vector_indexes(db, user.id)
    except Exception:  # noqa: BLE001
        indexes = {"error": "Vector index provisioning failed."}

    return {
        "status": "ok",
        "db": conn.db_name,
        "collections": collections,
        "vector_indexes": indexes,
        "message": f"Pinged {conn.db_name} successfully",
    }


# [RCF:PROTECTED]
@router.post("/vector-indexes")
# [RCF:PROTECTED]
async def create_vector_indexes(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create any missing Atlas vector indexes. Safe to call repeatedly."""
    try:
        return await memory_service.ensure_vector_indexes(db, user.id)
    except memory_service.MemoryError as e:
        raise HTTPException(status_code=400, detail=str(e))


# [RCF:PROTECTED]
@router.put("/{conn_id}", response_model=MongoResponse)
# [RCF:PROTECTED]
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
# [RCF:PROTECTED]
        conn.connection_string_encrypted = encrypt(body.connection_string)
        
    await db.commit()
    await db.refresh(conn)
    invalidate_mongo_client(user.id)
    return conn


# [RCF:PROTECTED]
@router.delete("/{conn_id}", status_code=204)
# [RCF:PROTECTED]
async def delete_mongo(conn_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MongoConnection).where(MongoConnection.id == conn_id, MongoConnection.user_id == user.id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    await db.delete(conn)
    await db.commit()
    invalidate_mongo_client(user.id)


# ─────────────────────────────────────────────────────────────────────────────
# Uploaded documents — the text extracted from files, kept apart from facts.
# ─────────────────────────────────────────────────────────────────────────────


# [RCF:PROTECTED]
@router.get("/documents")
# [RCF:PROTECTED]
async def list_documents(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """One row per uploaded document, newest first."""
    return await memory_service.list_documents(db, user.id)


# [RCF:PROTECTED]
@router.get("/documents/search")
# [RCF:PROTECTED]
async def search_documents(
    q: str,
    filename: str | None = None,
    limit: int = 5,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vector-search the text of uploaded documents."""
    if not q.strip():
        raise HTTPException(status_code=400, detail="q is required")
    limit = max(1, min(20, limit))
    try:
        return await memory_service.search_documents(
            db, user_id=user.id, query=q, filename=filename, limit=limit
        )
    except memory_service.MemoryError as e:
        raise HTTPException(status_code=400, detail=str(e))


# [RCF:PROTECTED]
@router.delete("/documents/{filename:path}", status_code=200)
# [RCF:PROTECTED]
async def delete_document(
    filename: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete every chunk of one uploaded document."""
    try:
        removed = await memory_service.delete_document(db, user_id=user.id, filename=filename)
    except memory_service.MemoryError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not removed:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"filename": filename, "deleted_chunks": removed}


# [RCF:PROTECTED]
@router.post("/documents/migrate-legacy")
# [RCF:PROTECTED]
async def migrate_legacy_documents(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Move pre-split file chunks out of shared facts into the document pool.

    Explicit rather than automatic: it rewrites the user's own Atlas data, so it
    runs when they ask for it. Safe to run twice.
    """
    try:
        return await memory_service.migrate_legacy_file_chunks(db, user_id=user.id)
    except memory_service.MemoryError as e:
        raise HTTPException(status_code=400, detail=str(e))
