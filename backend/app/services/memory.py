# NOTICE: This file is protected under RCF-PL
"""Memory service — MongoDB Atlas Vector Search backend.

Layout:
  Postgres (canonical state):
    - mongo_connections: per-user Atlas cluster URIs.
    - llm_providers: auto-selected by priority (nvidia_nim → openai → custom → huggingface)
                     embedding_model field stores user's choice from UI
  MongoDB Atlas (per user, in their `db_name`):
    - agent_memories     — private per-agent facts (1 vector index)
    - shared_context     — facts visible to all agents of this user
    - document_chunks    — text extracted from uploaded files, retrieved on demand
    - conversation_summaries — rolled-up chat history (no vector for now)

Facts and documents are deliberately separate pools. A fact is an assertion
("Acme renewed in March"); a document chunk is raw source text. Mixing them put
29 slices of one spreadsheet into every agent's system prompt and pushed real
facts off the dashboard, so uploads now land in `document_chunks` and are
searched when asked for rather than injected always.

Embeddings: 2048-dimensional vectors from any connected provider.
Model selection: user chooses via UI (provider.embedding_model), fallback to provider defaults.

Atlas Vector Search indexes are provisioned from code by `ensure_vector_indexes`
(called when a connection is tested, and exposed as POST /mongodb/vector-indexes).
Each is named `vector_index` over `embedding`, 2048-dimensional, cosine, and
carries the filter fields its queries scope by:
  agent_memories:  filter on `user_id`, `agent_id`
  shared_context:  filter on `user_id`
  document_chunks: filter on `user_id`

Until an index exists — or while Atlas is still building it — the searches fall
back to a recency query, so data stays reachable but unranked. That fallback is
quiet by design, which is why the indexes are no longer left to be created by
hand: a missing one looks exactly like a working search that returns weak hits.
"""
from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

import certifi
import httpx
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from sqlalchemy import select

from app.crypto import decrypt
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.llm_provider import LLMProvider
from app.models.mongo_connection import MongoConnection

log = logging.getLogger(__name__)

# Target embedding dimension for all providers
EMBED_DIM = 2048
VECTOR_INDEX_NAME = "vector_index"

PRIVATE_COLLECTION = "agent_memories"
SHARED_COLLECTION = "shared_context"
SUMMARY_COLLECTION = "conversation_summaries"
# Uploaded-document chunks live apart from facts. A slice of a spreadsheet is not
# a fact — it has no subject and asserts nothing — so it must never be injected
# into every agent's prompt or listed as one. Retrieved on demand instead.
DOCUMENT_COLLECTION = "document_chunks"

# Uploads made before documents were split out were stored as shared facts
# carrying this tag. Fact reads exclude them rather than deleting them behind the
# user's back — `migrate_legacy_file_chunks` moves them across on request.
LEGACY_FILE_TAG = "file-upload"
LEGACY_FILE_FILTER: dict[str, Any] = {"tags": {"$ne": LEGACY_FILE_TAG}}
# Extra rows to over-fetch from vector search before dropping legacy chunks in
# Python, so a user whose top hits are all old file chunks still gets facts.
LEGACY_HEADROOM = 20

# Module-level client cache keyed by user_id, so we don't reopen sockets every call.
_client_cache: dict[int, tuple[AsyncIOMotorClient, str]] = {}


# [RCF:PROTECTED]
class MemoryError(Exception):
    """Raised when the memory backend is unreachable or misconfigured."""


# ─────────────────────────────────────────────────────────────────────────────
# Connection resolution
# ─────────────────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
async def _resolve_mongo(db: AsyncSession, user_id: int) -> MongoConnection:
    result = await db.execute(
        select(MongoConnection).where(MongoConnection.user_id == user_id)
    )
    conn = result.scalars().first()
    if not conn:
        raise MemoryError("No MongoDB connection configured for this user")
    return conn


# [RCF:PROTECTED]
async def get_mongo_db(db: AsyncSession, user_id: int) -> AsyncIOMotorDatabase:
    """Return an `AsyncIOMotorDatabase` bound to the user's configured cluster."""
    cached = _client_cache.get(user_id)
    if cached is None:
        conn = await _resolve_mongo(db, user_id)
        client = AsyncIOMotorClient(
# [RCF:PROTECTED]
            decrypt(conn.connection_string_encrypted),
            serverSelectionTimeoutMS=5000,
            tlsCAFile=certifi.where(),
        )
        _client_cache[user_id] = (client, conn.db_name)
        return client[conn.db_name]
    client, db_name = cached
    return client[db_name]


# [RCF:PROTECTED]
def invalidate_mongo_client(user_id: int) -> None:
    """Drop the cached client (call after a connection-string change)."""
    cached = _client_cache.pop(user_id, None)
    if cached:
        cached[0].close()


# ─────────────────────────────────────────────────────────────────────────────
# Vector index provisioning
# ─────────────────────────────────────────────────────────────────────────────

# Which filter fields each collection needs alongside its vector field. A filter
# path missing from the index makes `$vectorSearch` reject the query outright, so
# these mirror the `filter_` dicts built in `_vector_search` / `search_documents`.
VECTOR_INDEX_FILTERS: dict[str, tuple[str, ...]] = {
    PRIVATE_COLLECTION: ("user_id", "agent_id"),
    SHARED_COLLECTION: ("user_id",),
    DOCUMENT_COLLECTION: ("user_id",),
}


# [RCF:PROTECTED]
def _vector_index_definition(filters: tuple[str, ...]) -> dict[str, Any]:
    return {
        "fields": [
            {
                "type": "vector",
                "path": "embedding",
                "numDimensions": EMBED_DIM,
                "similarity": "cosine",
            },
            *({"type": "filter", "path": path} for path in filters),
        ]
    }


# [RCF:PROTECTED]
async def ensure_vector_indexes(
    db: AsyncSession, user_id: int
) -> dict[str, dict[str, Any]]:
    """Create any missing Atlas vector indexes for this user's collections.

    Previously these were created by hand in the Atlas UI, which meant a cluster
    could serve searches for months with an index silently absent — the searches
    still answered, from the recency fallback, so nothing looked broken while
    ranking was gone. Provisioning from code makes the index a property of the
    connection rather than of someone remembering.

    Idempotent: an index that already exists is reported, never recreated, and
    its definition is left alone. Returns one entry per collection with a
    `status` of `exists`, `created`, `unsupported` (not an Atlas cluster) or
    `error`.
    """
    mdb = await get_mongo_db(db, user_id)
    existing_collections = set(await mdb.list_collection_names())
    out: dict[str, dict[str, Any]] = {}

    for collection, filters in VECTOR_INDEX_FILTERS.items():
        entry: dict[str, Any] = {"status": "error"}
        out[collection] = entry
        try:
            # `createSearchIndexes` fails on a namespace that does not exist yet,
            # and document_chunks only appears on first upload. Create it empty so
            # the index is ready before the first document lands, not after.
            if collection not in existing_collections:
                await mdb.create_collection(collection)
                entry["collection_created"] = True

            names = [
                idx.get("name")
                async for idx in mdb[collection].list_search_indexes()
            ]
            if VECTOR_INDEX_NAME in names:
                entry["status"] = "exists"
                continue

            await mdb[collection].create_search_index({
                "name": VECTOR_INDEX_NAME,
                "type": "vectorSearch",
                "definition": _vector_index_definition(filters),
            })
            # Atlas builds the index asynchronously; it answers queries only once
            # it reaches `queryable`. Until then the caller keeps the fallback.
            entry["status"] = "created"
            entry["queryable"] = False
        except Exception as e:  # noqa: BLE001
            # Self-hosted MongoDB has no Atlas Search: report it rather than
            # failing the request, since everything else still works there.
            message = str(e)
            if "not supported" in message.lower() or "CommandNotFound" in message:
                entry["status"] = "unsupported"
            entry["detail"] = message[:300]
            log.warning(
                "Vector index provisioning for %s failed: %s", collection, message
            )

    return out


# ─────────────────────────────────────────────────────────────────────────────
# Embeddings (auto-select provider)
# ─────────────────────────────────────────────────────────────────────────────

# Provider priority for embeddings fallback
EMBEDDING_PROVIDER_PRIORITY = ["nvidia_nim", "openai", "custom", "huggingface"]

# Model mapping per provider type with fallback chains
# Each provider can have multiple models listed in priority order (first available wins)
EMBEDDING_MODELS = {
    "nvidia_nim": [
        "nvidia/nv-embedqa-e5-v5",  # Current recommended model (2048 dim)
        "nvidia/nv-embed-v2",        # Alternative (4096 dim, can be truncated)
        "baai/bge-m3",              # Fallback (1024 dim, needs padding)
    ],
    "openai": [
        "text-embedding-3-large",   # 3072 dim, can be truncated to 2048
        "text-embedding-3-small",   # 1536 dim, needs padding
        "text-embedding-ada-002",   # 1536 dim, legacy fallback
    ],
    "custom": None,  # Use whatever the custom endpoint provides
    "huggingface": [
        "sentence-transformers/all-mpnet-base-v2",  # 768 dim, needs padding
        "BAAI/bge-large-en-v1.5",                   # 1024 dim, fallback
    ],
}


# [RCF:PROTECTED]
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


# [RCF:PROTECTED]
async def embed(
    db: AsyncSession,
    user_id: int,
    text: str,
    *,
    input_type: str = "query",
) -> list[float]:
    """Embed text via available provider and return a 2048-dim vector.

    Args:
        input_type: NIM-specific hint for embedding optimisation.
            Use ``"query"`` for search queries (default) and
            ``"passage"`` for facts being indexed into the store.
    """
    provider = await _resolve_embedding_provider(db, user_id)
# [RCF:PROTECTED]
    api_key = decrypt(provider.api_key_encrypted) if provider.api_key_encrypted else None
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Use user-selected embedding model from UI, or fall back to defaults
    model = provider.embedding_model
    if not model:
        # Fallback to default models for provider type (try each in order)
        default_models = EMBEDDING_MODELS.get(provider.type)
        if isinstance(default_models, list):
            # Try each model in the fallback chain
            model = default_models[0]  # Start with first model
            # Store the full chain for retry logic
            model_chain = default_models
        elif default_models:
            model = default_models
            model_chain = [default_models]
        else:
            model_chain = []

    if not model and provider.models_available:
        # Try to extract first model from models_available (could be JSON string or text)
        try:
            import json
            models = json.loads(provider.models_available) if isinstance(provider.models_available, str) else provider.models_available
            if isinstance(models, list) and models:
                model = models[0]
                model_chain = models
        except Exception:
            model_chain = []

    # Final fallback: use a generic embedding model name
    if not model:
        model = "text-embedding-model"
        model_chain = [model]

    # Ensure model_chain is defined
    if 'model_chain' not in locals():
        model_chain = [model] if model else []

    url = f"{provider.base_url.rstrip('/')}/v1/embeddings"

    # OpenAI-style payload (works for NIM, OpenAI, most custom endpoints)
    payload = {
        "model": model,
        "input": [text],
        "encoding_format": "float",
    }

    # NIM-specific parameters: input_type must match the operation —
    # "passage" for facts being stored, "query" for search queries.
    if provider.type == "nvidia_nim":
        payload["input_type"] = input_type
        payload["truncate"] = "END"

    # OpenAI dimension control to match our 2048 requirement.
    # Only the text-embedding-3-* family supports the `dimensions` param;
    # older models (e.g. text-embedding-ada-002) reject it with HTTP 400.
    if provider.type == "openai" and "text-embedding-3" in (model or ""):
        payload["dimensions"] = EMBED_DIM

    # Try each model in the chain until one succeeds
    last_error = None
    for attempt_model in model_chain:
        payload["model"] = attempt_model

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                # Success! Break out of retry loop
                break
            except httpx.HTTPStatusError as e:
                last_error = e
                # If model reached EOL (410) or not found (404), try next model in chain
                if e.response.status_code in (404, 410) and model_chain.index(attempt_model) < len(model_chain) - 1:
                    log.warning(
                        f"Embedding model {attempt_model} unavailable (HTTP {e.response.status_code}), "
                        f"trying fallback model..."
                    )
                    continue
                # For other errors or last model in chain, raise
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

# [RCF:PROTECTED]
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

    vector = await embed(db, user_id, fact, input_type="passage")
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


# [RCF:PROTECTED]
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


# [RCF:PROTECTED]
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
    try:
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
    except Exception as e:
        log.warning(
            "Vector search aggregation failed, falling back to recent facts query: %s",
            e,
        )
        try:
            cursor = coll.find(filter_).sort("created_at", -1).limit(limit)
            async for doc in cursor:
                out.append({
                    "id": str(doc["_id"]),
                    "fact": doc.get("fact", ""),
                    "tags": doc.get("tags", []),
                    "agent_id": doc.get("agent_id"),
                    "visibility": visibility,
                    "score": 0.5,  # Default score for fallback matches
                    "created_at": doc.get("created_at"),
                })
        except Exception as fe:
            log.exception("Fallback query also failed: %s", fe)
    return out


# [RCF:PROTECTED]
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
        # Legacy file chunks are documents, not facts — keep them out of the list.
        flt = {"user_id": user_id, **LEGACY_FILE_FILTER}
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


# [RCF:PROTECTED]
async def count_memories(db: AsyncSession, user_id: int) -> int:
    """Return total number of memory documents (private + shared) for a user.
    
    Returns 0 if MongoDB is not configured or unreachable.
    """
    try:
        mdb = await get_mongo_db(db, user_id)
        private_count = await mdb[PRIVATE_COLLECTION].count_documents({"user_id": user_id})
        shared_count = await mdb[SHARED_COLLECTION].count_documents(
            {"user_id": user_id, **LEGACY_FILE_FILTER}
        )
        return private_count + shared_count
    except Exception:
        return 0


# [RCF:PROTECTED]
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


# [RCF:PROTECTED]
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
            limit=limit + LEGACY_HEADROOM,
            filter_={"user_id": user_id},
            visibility="shared",
        )
    except Exception:  # noqa: BLE001
        return ""

    # Drop legacy document chunks here rather than in the $vectorSearch filter:
    # Atlas only filters on fields declared in the index, and `tags` is not one,
    # so filtering there would error out into the recency fallback and lose
    # ranking altogether. Over-fetch, then trim.
    results = [r for r in results if LEGACY_FILE_TAG not in (r.get("tags") or [])]
    results = results[:limit]

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
# Uploaded documents
# ─────────────────────────────────────────────────────────────────────────────

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100


# [RCF:PROTECTED]
def chunk_text_content(text: str, *, tabular: bool = False) -> list[str]:
    """Split extracted document text into chunks for embedding.

    Prose is split on character count with an overlap, which is fine — a sentence
    cut in half still reads. A table is not: slicing mid-row strips a number from
    its column, and the header only ever appears in the first chunk, so every
    later chunk becomes unlabelled figures. For tabular text we therefore split
    on line boundaries and repeat the header on each chunk.

    Pure and side-effect free so the chunking can be tested without Mongo.
    """
    if not text.strip():
        return []

    if not tabular:
        chunks: list[str] = []
        i = 0
        step = CHUNK_SIZE - CHUNK_OVERLAP
        while i < len(text):
            chunks.append(text[i : i + CHUNK_SIZE])
            i += step
        return chunks

    lines = text.splitlines()
    if not lines:
        return []

    header = lines[0]
    chunks = []
    current: list[str] = []
    # The header costs one line of budget in every chunk after the first.
    size = len(header)

    for line in lines[1:]:
        # +1 for the newline joining it to what is already buffered.
        if current and size + len(line) + 1 > CHUNK_SIZE:
            chunks.append("\n".join([header, *current]))
            current = []
            size = len(header)
        current.append(line)
        size += len(line) + 1

    if current:
        chunks.append("\n".join([header, *current]))
    elif not chunks:
        # Header with no data rows — still worth indexing.
        chunks.append(header)

    return chunks


# [RCF:PROTECTED]
async def store_document_chunk(
    db: AsyncSession,
    *,
    user_id: int,
    filename: str,
    text: str,
    part: int,
    total_parts: int,
) -> dict[str, Any]:
    """Insert one chunk of an uploaded document.

    Kept out of `store_memory` on purpose: these are not facts, they are not
    visible to `list_memories`, and they are never injected into a system prompt.
    """
    vector = await embed(db, user_id, text, input_type="passage")
    mdb = await get_mongo_db(db, user_id)

    result = await mdb[DOCUMENT_COLLECTION].insert_one({
        "user_id": user_id,
        "filename": filename,
        "text": text,
        "embedding": vector,
        "part": part,
        "total_parts": total_parts,
        "created_at": datetime.now(timezone.utc),
    })
    return {"id": str(result.inserted_id), "filename": filename, "part": part}


# [RCF:PROTECTED]
async def search_documents(
    db: AsyncSession,
    *,
    user_id: int,
    query: str,
    filename: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Vector-search uploaded document chunks, most relevant first.

    This is the pull side of the split: an agent reaches for a document when the
    conversation calls for it, instead of every document riding along in every
    prompt.
    """
    vector = await embed(db, user_id, query)
    mdb = await get_mongo_db(db, user_id)

    filter_: dict[str, Any] = {"user_id": user_id}
    if filename:
        filter_["filename"] = filename

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
                "filename": 1,
                "text": 1,
                "part": 1,
                "total_parts": 1,
                "created_at": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    def _row(doc: dict[str, Any], score: float | None = None) -> dict[str, Any]:
        return {
            "id": str(doc["_id"]),
            "filename": doc.get("filename", ""),
            "text": doc.get("text", ""),
            "part": doc.get("part"),
            "total_parts": doc.get("total_parts"),
            "created_at": doc.get("created_at"),
            "score": doc.get("score", 0.0) if score is None else score,
        }

    out: list[dict[str, Any]] = []
    try:
        async for doc in mdb[DOCUMENT_COLLECTION].aggregate(pipeline):
            out.append(_row(doc))
    except Exception as e:
        # No vector index yet (it is created by hand in Atlas): fall back to
        # recency so an upload is still reachable, just not ranked.
        log.warning("Document vector search failed, falling back to recent chunks: %s", e)
        try:
            cursor = (
                mdb[DOCUMENT_COLLECTION]
                .find(filter_, projection={"embedding": 0})
                .sort("created_at", -1)
                .limit(limit)
            )
            async for doc in cursor:
                out.append(_row(doc, score=0.5))
        except Exception as fe:
            log.exception("Document fallback query also failed: %s", fe)

    return out


# [RCF:PROTECTED]
async def list_documents(db: AsyncSession, user_id: int) -> list[dict[str, Any]]:
    """Return one row per uploaded document, newest first."""
    mdb = await get_mongo_db(db, user_id)
    pipeline = [
        {"$match": {"user_id": user_id}},
        {
            "$group": {
                "_id": "$filename",
                "chunks": {"$sum": 1},
                "total_parts": {"$max": "$total_parts"},
                "created_at": {"$max": "$created_at"},
            }
        },
        {"$sort": {"created_at": -1}},
    ]
    out: list[dict[str, Any]] = []
    try:
        async for doc in mdb[DOCUMENT_COLLECTION].aggregate(pipeline):
            out.append({
                "filename": doc["_id"],
                "chunks": doc.get("chunks", 0),
                "total_parts": doc.get("total_parts"),
                "created_at": doc.get("created_at"),
            })
    except Exception as e:
        log.warning("Failed to list documents for user %s: %s", user_id, e)
    return out


# [RCF:PROTECTED]
async def migrate_legacy_file_chunks(db: AsyncSession, *, user_id: int) -> dict[str, int]:
    """Move pre-split file chunks out of shared facts and into `document_chunks`.

    Reuses each document's existing embedding rather than re-embedding, so this
    costs no provider calls. The old `fact` text carries a
    "Content from uploaded file 'x' (part n/m):" preamble; it is stripped so the
    stored text is the content, not a sentence about the content.

    Idempotent: a chunk is deleted from `shared_context` only after its
    replacement is written, so an interrupted run resumes safely.
    """
    import re

    mdb = await get_mongo_db(db, user_id)
    shared = mdb[SHARED_COLLECTION]
    docs = mdb[DOCUMENT_COLLECTION]

    preamble = re.compile(
        r"^Content from uploaded file '(?P<name>.*?)' \(part (?P<part>\d+)/(?P<total>\d+)\):\n",
        re.DOTALL,
    )

    moved = 0
    failed = 0
    cursor = shared.find({"user_id": user_id, "tags": LEGACY_FILE_TAG})
    async for doc in cursor:
        fact = doc.get("fact") or ""
        match = preamble.match(fact)

        tags = [t for t in (doc.get("tags") or []) if t != LEGACY_FILE_TAG]
        filename = match.group("name") if match else (tags[0] if tags else "unknown")
        text = fact[match.end():] if match else fact

        try:
            await docs.insert_one({
                "user_id": user_id,
                "filename": filename,
                "text": text,
                "embedding": doc.get("embedding"),
                "part": int(match.group("part")) if match else None,
                "total_parts": int(match.group("total")) if match else None,
                "created_at": doc.get("created_at") or datetime.now(timezone.utc),
                "migrated": True,
            })
            await shared.delete_one({"_id": doc["_id"]})
            moved += 1
        except Exception as e:  # noqa: BLE001
            log.warning("Failed to migrate legacy chunk %s: %s", doc.get("_id"), e)
            failed += 1

    log.info("Migrated %d legacy file chunks for user %s (%d failed)", moved, user_id, failed)
    return {"moved": moved, "failed": failed}


# [RCF:PROTECTED]
async def delete_document(db: AsyncSession, *, user_id: int, filename: str) -> int:
    """Delete every chunk of one document. Returns how many were removed."""
    mdb = await get_mongo_db(db, user_id)
    res = await mdb[DOCUMENT_COLLECTION].delete_many(
        {"user_id": user_id, "filename": filename}
    )
    return int(res.deleted_count)


# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
async def index_file_in_vector_search(
    user_id: int,
    filename: str,
    mime: str,
) -> None:
    """Extract text from the uploaded file and index it in the shared context."""
    from app.database import async_session
    from app.services import media_storage
    import io

    async with async_session() as db:
        handle = await media_storage.resolve(db, user_id, filename)
        if not handle:
            log.warning("Could not resolve file handle for indexing: %s", filename)
            return

        data = await media_storage.get_bytes(db, user_id, handle)
        if not data:
            log.warning("Could not read file bytes for indexing: %s", filename)
            return

        text_content = ""
        mime_lower = mime.lower()
        # Tabular text is chunked line-wise with the header repeated, so no chunk
        # arrives as columns without names.
        is_tabular = False

        # 1. Text files
        if mime_lower.startswith("text/") or mime_lower in (
            "application/json", "application/javascript",
            "text/javascript", "text/csv", "application/xml",
            "application/x-javascript"
        ):
            try:
                text_content = data.decode("utf-8", errors="ignore")
                # A CSV is a table too: keep its header on every chunk.
                is_tabular = mime_lower == "text/csv" or filename.lower().endswith(".csv")
            except Exception as e:
                log.exception("Failed to decode text file: %s", e)
                return

        # 2. Excel spreadsheets
        elif mime_lower in (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel"
        ):
            try:
                import pandas as pd
                # Every sheet, not just the first: read_excel(sheet_name=None)
                # returns an ordered dict so a workbook does not silently lose tabs.
                sheets = pd.read_excel(io.BytesIO(data), sheet_name=None)
                parts = []
                for sheet_name, df in sheets.items():
                    if df.empty:
                        continue
                    # to_csv, not to_string: to_string is a console rendering that
                    # emits "NaN" for blanks and truncates wide frames. NaN reads to
                    # an LLM as a cell value, which is a fabricated one.
                    body = df.to_csv(index=False, na_rep="")
                    parts.append(f"## Sheet: {sheet_name}\n{body}")
                text_content = "\n\n".join(parts)
                is_tabular = True
            except Exception as e:
                log.warning("Failed to index Excel file %s: %s", filename, e)
                return

        # 3. PDF documents (if pypdf is installed/importable)
        elif mime_lower == "application/pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(data))
                pages_text = []
                for page in reader.pages:
                    t = page.extract_text()
                    if t:
                        pages_text.append(t)
                text_content = "\n".join(pages_text)
            except Exception:
                log.warning("Failed to extract PDF %s (pypdf not installed/working)", filename)
                return

        if not text_content.strip():
            log.info("No extractable text content found in file %s", filename)
            return

        chunks = chunk_text_content(text_content, tabular=is_tabular)

        log.info("Indexing %d chunks from file %s in document search...", len(chunks), filename)
        for idx, chunk in enumerate(chunks):
            try:
                await store_document_chunk(
                    db,
                    user_id=user_id,
                    filename=filename,
                    text=chunk,
                    part=idx + 1,
                    total_parts=len(chunks),
                )
            except Exception as e:
                log.exception("Failed to store document chunk for file %s: %s", filename, e)


# [RCF:PROTECTED]
async def ping(db: AsyncSession, user_id: int) -> dict[str, Any]:
    """Verify the configured Atlas cluster is reachable."""
    mdb = await get_mongo_db(db, user_id)
    pong = await mdb.command("ping")
    return {"ok": bool(pong.get("ok")), "db": mdb.name}
