"""Memory service — MongoDB Atlas Vector Search backend.

Layout:
  Postgres (canonical state):
    - mongo_connections: per-user Atlas cluster URIs.
    - llm_providers: auto-selected by priority (nvidia_nim → openai → custom → huggingface)
                     embedding_model field stores user's choice from UI
  MongoDB Atlas (per user, in their `db_name`):
    - agent_memories     — private per-agent facts (1 vector index)
    - shared_context     — facts visible to all agents of this user
    - conversation_summaries — rolled-up chat history (no vector for now)

Embeddings: 2048-dimensional vectors from any connected provider.
Model selection: user chooses via UI (provider.embedding_model), fallback to provider defaults.

Atlas Vector Search indexes (must be created manually in the Atlas UI):
  Collection: agent_memories       Index: vector_index   field: embedding   dim: 2048   similarity: cosine
  Collection: shared_context       Index: vector_index   field: embedding   dim: 2048   similarity: cosine

Both indexes additionally need filter fields so we can scope queries:
  agent_memories: filter on `agent_id`, `user_id`
  shared_context: filter on `user_id`
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import certifi
import httpx
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from sqlalchemy import select

from app.crypto import decrypt
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_provider import LLMProvider
from app.models.mongo_connection import MongoConnection

# Target embedding dimension for all providers
EMBED_DIM = 2048
VECTOR_INDEX_NAME = "vector_index"

PRIVATE_COLLECTION = "agent_memories"
SHARED_COLLECTION = "shared_context"
SUMMARY_COLLECTION = "conversation_summaries"

# Module-level client cache keyed by user_id, so we don't reopen sockets every call.
_client_cache: dict[int, tuple[AsyncIOMotorClient, str]] = {}


class MemoryError(Exception):
    """Raised when the memory backend is unreachable or misconfigured."""


# ─────────────────────────────────────────────────────────────────────────────
# Connection resolution
# ─────────────────────────────────────────────────────────────────────────────

async def _resolve_mongo(db: AsyncSession, user_id: int) -> MongoConnection:
    result = await db.execute(
        select(MongoConnection).where(MongoConnection.user_id == user_id)
    )
    conn = result.scalars().first()
    if not conn:
        raise MemoryError("No MongoDB connection configured for this user")
    return conn


async def get_mongo_db(db: AsyncSession, user_id: int) -> AsyncIOMotorDatabase:
    """Return an `AsyncIOMotorDatabase` bound to the user's configured cluster."""
    cached = _client_cache.get(user_id)
    if cached is None:
        conn = await _resolve_mongo(db, user_id)
        client = AsyncIOMotorClient(
            decrypt(conn.connection_string_encrypted),
            serverSelectionTimeoutMS=5000,
            tlsCAFile=certifi.where(),
        )
        _client_cache[user_id] = (client, conn.db_name)
        return client[conn.db_name]
    client, db_name = cached
    return client[db_name]


def invalidate_mongo_client(user_id: int) -> None:
    """Drop the cached client (call after a connection-string change)."""
    cached = _client_cache.pop(user_id, None)
    if cached:
        cached[0].close()


# ─────────────────────────────────────────────────────────────────────────────
# Embeddings (auto-select provider)
# ─────────────────────────────────────────────────────────────────────────────

# Provider priority for embeddings fallback
EMBEDDING_PROVIDER_PRIORITY = ["nvidia_nim", "openai", "custom", "huggingface"]

# Model mapping per provider type
EMBEDDING_MODELS = {
    "nvidia_nim": "nvidia/llama-nemotron-embed-1b-v2",
    "openai": "text-embedding-3-large",  # 3072 dim, can be truncated to 2048
    "custom": None,  # Use whatever the custom endpoint provides
    "huggingface": "sentence-transformers/all-mpnet-base-v2",  # 768 dim, needs padding
}


async def _resolve_embedding_provider(db: AsyncSession, user_id: int) -> LLMProvider:
    """Select first available embedding provider by priority."""
    for provider_type in EMBEDDING_PROVIDER_PRIORITY:
        result = await db.execute(
            select(LLMProvider).where(
                LLMProvider.user_id == user_id,
                LLMProvider.type == provider_type,
                LLMProvider.status == "connected",
            )
        )
        provider = result.scalars().first()
        if provider:
            return provider

    raise MemoryError(
        f"No embedding provider configured. Need one of: {', '.join(EMBEDDING_PROVIDER_PRIORITY)}"
    )


async def embed(db: AsyncSession, user_id: int, text: str) -> list[float]:
    """Embed text via available provider and return a 2048-dim vector."""
    provider = await _resolve_embedding_provider(db, user_id)
    api_key = decrypt(provider.api_key_encrypted) if provider.api_key_encrypted else None
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Use user-selected embedding model from UI, or fall back to defaults
    model = provider.embedding_model
    if not model:
        # Fallback to default model for provider type
        model = EMBEDDING_MODELS.get(provider.type)

    if not model and provider.models_available:
        # Try to extract first model from models_available (could be JSON string or text)
        try:
            import json
            models = json.loads(provider.models_available) if isinstance(provider.models_available, str) else provider.models_available
            if isinstance(models, list) and models:
                model = models[0]
        except Exception:
            pass

    # Final fallback: use a generic embedding model name
    if not model:
        model = "text-embedding-model"

    url = f"{provider.base_url.rstrip('/')}/v1/embeddings"

    # OpenAI-style payload (works for NIM, OpenAI, most custom endpoints)
    payload = {
        "model": model,
        "input": [text],
        "encoding_format": "float",
    }

    # NIM-specific parameters
    if provider.type == "nvidia_nim":
        payload["input_type"] = "query"
        payload["truncate"] = "END"

    # OpenAI dimension control to match our 2048 requirement
    if provider.type == "openai":
        payload["dimensions"] = EMBED_DIM

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise MemoryError(
                f"Embedding failed ({provider.type}): HTTP {e.response.status_code}: {e.response.text[:300]}"
            ) from e
        except httpx.HTTPError as e:
            raise MemoryError(f"Embedding request failed ({provider.type}): {e}") from e

    data = resp.json()
    try:
        vec = data["data"][0]["embedding"]
    except (KeyError, IndexError, TypeError) as e:
        raise MemoryError(
            f"Unexpected embedding response from {provider.type}: {str(data)[:200]}"
        ) from e

    # Validate and normalize dimensions
    if not isinstance(vec, list):
        raise MemoryError(f"Embedding is not a list: {type(vec)}")

    vec_len = len(vec)
    if vec_len == EMBED_DIM:
        return vec
    elif vec_len > EMBED_DIM:
        # Truncate (e.g., OpenAI text-embedding-3-large can be 3072)
        return vec[:EMBED_DIM]
    else:
        # Pad with zeros (e.g., smaller models like 768-dim)
        return vec + ([0.0] * (EMBED_DIM - vec_len))


# ─────────────────────────────────────────────────────────────────────────────
# Memory CRUD
# ─────────────────────────────────────────────────────────────────────────────

async def store_memory(
    db: AsyncSession,
    *,
    user_id: int,
    agent_id: int | None,
    fact: str,
    visibility: str = "private",
    tags: list[str] | None = None,
    session_id: int | None = None,
) -> dict[str, Any]:
    """Insert a fact into private (agent-scoped) or shared collection."""
    if visibility not in ("private", "shared"):
        raise MemoryError(f"Invalid visibility: {visibility}")
    if visibility == "private" and agent_id is None:
        raise MemoryError("Private memories require an agent_id")

    vector = await embed(db, user_id, fact)
    mdb = await get_mongo_db(db, user_id)

    doc: dict[str, Any] = {
        "user_id": user_id,
        "fact": fact,
        "embedding": vector,
        "tags": tags or [],
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc),
    }
    if visibility == "private":
        doc["agent_id"] = agent_id
        coll = mdb[PRIVATE_COLLECTION]
    else:
        coll = mdb[SHARED_COLLECTION]

    result = await coll.insert_one(doc)
    return {"id": str(result.inserted_id), "visibility": visibility}


async def search_memory(
    db: AsyncSession,
    *,
    user_id: int,
    agent_id: int | None,
    query: str,
    scope: str = "both",
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Vector-search relevant facts in private (agent-scoped) and/or shared pools."""
    if scope not in ("private", "shared", "both"):
        raise MemoryError(f"Invalid scope: {scope}")

    vector = await embed(db, user_id, query)
    mdb = await get_mongo_db(db, user_id)

    results: list[dict[str, Any]] = []

    if scope in ("private", "both") and agent_id is not None:
        results.extend(await _vector_search(
            mdb[PRIVATE_COLLECTION],
            vector=vector,
            limit=limit,
            filter_={"user_id": user_id, "agent_id": agent_id},
            visibility="private",
        ))

    if scope in ("shared", "both"):
        results.extend(await _vector_search(
            mdb[SHARED_COLLECTION],
            vector=vector,
            limit=limit,
            filter_={"user_id": user_id},
            visibility="shared",
        ))

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:limit]


async def _vector_search(
    coll,
    *,
    vector: list[float],
    limit: int,
    filter_: dict[str, Any],
    visibility: str,
) -> list[dict[str, Any]]:
    pipeline = [
        {
            "$vectorSearch": {
                "index": VECTOR_INDEX_NAME,
                "path": "embedding",
                "queryVector": vector,
                "numCandidates": max(limit * 10, 50),
                "limit": limit,
                "filter": filter_,
            }
        },
        {
            "$project": {
                "_id": 1,
                "fact": 1,
                "tags": 1,
                "agent_id": 1,
                "created_at": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]
    out: list[dict[str, Any]] = []
    async for doc in coll.aggregate(pipeline):
        out.append({
            "id": str(doc["_id"]),
            "fact": doc.get("fact", ""),
            "tags": doc.get("tags", []),
            "agent_id": doc.get("agent_id"),
            "visibility": visibility,
            "score": doc.get("score", 0.0),
            "created_at": doc.get("created_at"),
        })
    return out


async def list_memories(
    db: AsyncSession,
    *,
    user_id: int,
    agent_id: int | None,
    scope: str = "both",
    q: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return facts ordered by created_at desc. No vector search.

    `q` does a case-insensitive substring match on `fact` (and `tags`).
    `scope=private` requires `agent_id`; `shared` ignores it; `both` merges.
    """
    if scope not in ("private", "shared", "both"):
        raise MemoryError(f"Invalid scope: {scope}")

    mdb = await get_mongo_db(db, user_id)
    out: list[dict[str, Any]] = []

    text_filter: dict[str, Any] = {}
    if q and q.strip():
        rx = {"$regex": q.strip(), "$options": "i"}
        text_filter = {"$or": [{"fact": rx}, {"tags": rx}]}

    if scope in ("private", "both") and agent_id is not None:
        flt: dict[str, Any] = {"user_id": user_id, "agent_id": agent_id}
        if text_filter:
            flt = {"$and": [flt, text_filter]}
        cursor = mdb[PRIVATE_COLLECTION].find(
            flt,
            projection={"embedding": 0},
        ).sort("created_at", -1).limit(limit)
        async for doc in cursor:
            out.append({
                "id": str(doc["_id"]),
                "fact": doc.get("fact", ""),
                "tags": doc.get("tags", []),
                "agent_id": doc.get("agent_id"),
                "visibility": "private",
                "created_at": doc.get("created_at"),
                "session_id": doc.get("session_id"),
            })

    if scope in ("shared", "both"):
        flt = {"user_id": user_id}
        if text_filter:
            flt = {"$and": [flt, text_filter]}
        cursor = mdb[SHARED_COLLECTION].find(
            flt,
            projection={"embedding": 0},
        ).sort("created_at", -1).limit(limit)
        async for doc in cursor:
            out.append({
                "id": str(doc["_id"]),
                "fact": doc.get("fact", ""),
                "tags": doc.get("tags", []),
                "agent_id": doc.get("agent_id"),
                "visibility": "shared",
                "created_at": doc.get("created_at"),
                "session_id": doc.get("session_id"),
            })

    out.sort(key=lambda r: r.get("created_at") or datetime.min, reverse=True)
    return out[:limit]


async def count_memories(db: AsyncSession, user_id: int) -> int:
    """Return total number of memory documents (private + shared) for a user.
    
    Returns 0 if MongoDB is not configured or unreachable.
    """
    try:
        mdb = await get_mongo_db(db, user_id)
        private_count = await mdb[PRIVATE_COLLECTION].count_documents({"user_id": user_id})
        shared_count = await mdb[SHARED_COLLECTION].count_documents({"user_id": user_id})
        return private_count + shared_count
    except Exception:
        return 0


async def delete_memory(
    db: AsyncSession,
    *,
    user_id: int,
    agent_id: int | None,
    memory_id: str,
) -> bool:
    """Delete a memory by id. Scoped to user_id (and agent_id for private)."""
    from bson import ObjectId
    try:
        oid = ObjectId(memory_id)
    except Exception as e:
        raise MemoryError(f"Invalid memory_id: {memory_id}") from e

    mdb = await get_mongo_db(db, user_id)

    if agent_id is not None:
        res = await mdb[PRIVATE_COLLECTION].delete_one(
            {"_id": oid, "user_id": user_id, "agent_id": agent_id}
        )
        if res.deleted_count:
            return True

    res = await mdb[SHARED_COLLECTION].delete_one({"_id": oid, "user_id": user_id})
    return bool(res.deleted_count)


# ─────────────────────────────────────────────────────────────────────────────
# Shared-context injection
# ─────────────────────────────────────────────────────────────────────────────

SHARED_BLOCK_OPEN = "<shared_context>"
SHARED_BLOCK_CLOSE = "</shared_context>"


async def build_shared_context_block(
    db: AsyncSession,
    *,
    user_id: int,
    query: str,
    limit: int = 5,
) -> str:
    """Vector-search shared facts and format them as a system-prompt block.

    Returns an empty string on any failure (no embeddings provider, no Mongo
    connection, vector index missing, etc.) — injection is best-effort.
    """
    if not query or not query.strip():
        return ""

    try:
        vector = await embed(db, user_id, query)
        mdb = await get_mongo_db(db, user_id)
        results = await _vector_search(
            mdb[SHARED_COLLECTION],
            vector=vector,
            limit=limit,
            filter_={"user_id": user_id},
            visibility="shared",
        )
    except Exception:  # noqa: BLE001
        return ""

    if not results:
        return ""

    lines = [SHARED_BLOCK_OPEN]
    for r in results:
        fact = (r.get("fact") or "").strip()
        if not fact:
            continue
        tags = r.get("tags") or []
        tag_str = f" [{', '.join(tags)}]" if tags else ""
        lines.append(f"- {fact}{tag_str}")
    lines.append(SHARED_BLOCK_CLOSE)
    if len(lines) <= 2:
        return ""
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────

async def ping(db: AsyncSession, user_id: int) -> dict[str, Any]:
    """Verify the configured Atlas cluster is reachable."""
    mdb = await get_mongo_db(db, user_id)
    pong = await mdb.command("ping")
    return {"ok": bool(pong.get("ok")), "db": mdb.name}
