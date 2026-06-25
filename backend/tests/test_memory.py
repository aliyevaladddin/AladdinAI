# NOTICE: This file is protected under RCF-PL
"""Tests for app.services.memory.

Strategy:
- embed() and its helpers are tested by mocking httpx and the DB provider lookup.
- store_memory / search_memory / list_memories / delete_memory are tested
  by mocking get_mongo_db and embed() — no real MongoDB or LLM needed.
- Connection-cache helpers (invalidate_mongo_client) tested directly.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.memory import (
    EMBED_DIM,
    MemoryError,
    _client_cache,
    build_shared_context_block,
    count_memories,
    embed,
    invalidate_mongo_client,
    store_memory,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers for making mock objects
# ─────────────────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
def _make_provider(provider_type: str = "openai", base_url: str = "https://api.openai.com"):
    p = MagicMock()
    p.type = provider_type
    p.base_url = base_url
# [RCF:PROTECTED]
    p.api_key_encrypted = None
    p.embedding_model = "text-embedding-3-large"
    p.models_available = None
    return p


# [RCF:PROTECTED]
def _make_db():
    """AsyncSession mock that returns a provider from execute()."""
    db = AsyncMock()
    return db


# ─────────────────────────────────────────────────────────────────────────────
# embed() — dimension normalisation
# ─────────────────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_embed_exact_dim():
    """Provider returns exactly 2048-dim vector — returned as-is."""
    vec = [0.1] * EMBED_DIM
    db = _make_db()
    provider = _make_provider()

    with (
        patch("app.services.memory._resolve_embedding_provider", new_callable=AsyncMock, return_value=provider),
        patch("app.services.memory.decrypt", return_value="sk-test"),
        patch("app.services.memory.httpx.AsyncClient") as mock_client_cls,
    ):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": [{"embedding": vec}]}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        result = await embed(db, user_id=1, text="hello world")

    assert len(result) == EMBED_DIM
    assert result == vec


# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_embed_truncates_oversized_vector():
    """Provider returns 3072-dim vector — truncated to 2048."""
    vec = [0.5] * 3072
    db = _make_db()
    provider = _make_provider()

    with (
        patch("app.services.memory._resolve_embedding_provider", new_callable=AsyncMock, return_value=provider),
        patch("app.services.memory.decrypt", return_value=None),
        patch("app.services.memory.httpx.AsyncClient") as mock_client_cls,
    ):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": [{"embedding": vec}]}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        result = await embed(db, user_id=1, text="hello")

    assert len(result) == EMBED_DIM
    assert result == vec[:EMBED_DIM]


# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_embed_pads_undersized_vector():
    """Provider returns 768-dim vector — padded with zeros to 2048."""
    vec = [1.0] * 768
    db = _make_db()
    provider = _make_provider("huggingface", "https://hf.co")
    provider.embedding_model = "sentence-transformers/all-mpnet-base-v2"

    with (
        patch("app.services.memory._resolve_embedding_provider", new_callable=AsyncMock, return_value=provider),
        patch("app.services.memory.decrypt", return_value=None),
        patch("app.services.memory.httpx.AsyncClient") as mock_client_cls,
    ):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": [{"embedding": vec}]}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        result = await embed(db, user_id=1, text="hello")

    assert len(result) == EMBED_DIM
    assert result[:768] == vec
    assert result[768:] == [0.0] * (EMBED_DIM - 768)


# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_embed_nim_uses_correct_input_type_passage():
    """For NIM provider, store_memory path must send input_type=passage."""
    vec = [0.1] * EMBED_DIM
    db = _make_db()
    provider = _make_provider("nvidia_nim", "https://integrate.api.nvidia.com")
    provider.embedding_model = "nvidia/llama-nemotron-embed-1b-v2"

    captured_payload = {}

# [RCF:PROTECTED]
    async def fake_post(url, json=None, headers=None):
        captured_payload.update(json or {})
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": [{"embedding": vec}]}
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with (
        patch("app.services.memory._resolve_embedding_provider", new_callable=AsyncMock, return_value=provider),
        patch("app.services.memory.decrypt", return_value="nimkey"),
        patch("app.services.memory.httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=fake_post)
        mock_client_cls.return_value = mock_client

        await embed(db, user_id=1, text="a fact to store", input_type="passage")

    assert captured_payload.get("input_type") == "passage"


# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_embed_nim_uses_query_for_search():
    """For NIM provider, search path must send input_type=query (default)."""
    vec = [0.1] * EMBED_DIM
    db = _make_db()
    provider = _make_provider("nvidia_nim", "https://integrate.api.nvidia.com")
    provider.embedding_model = "nvidia/llama-nemotron-embed-1b-v2"

    captured_payload = {}

# [RCF:PROTECTED]
    async def fake_post(url, json=None, headers=None):
        captured_payload.update(json or {})
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": [{"embedding": vec}]}
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    with (
        patch("app.services.memory._resolve_embedding_provider", new_callable=AsyncMock, return_value=provider),
        patch("app.services.memory.decrypt", return_value="nimkey"),
        patch("app.services.memory.httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=fake_post)
        mock_client_cls.return_value = mock_client

        # Default input_type="query"
        await embed(db, user_id=1, text="what do I know about Python?")

    assert captured_payload.get("input_type") == "query"


# ─────────────────────────────────────────────────────────────────────────────
# store_memory
# ─────────────────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_store_memory_private():
    """store_memory inserts into agent_memories collection."""
    db = _make_db()
    fake_vec = [0.1] * EMBED_DIM

    fake_coll = AsyncMock()
    fake_coll.insert_one = AsyncMock(return_value=MagicMock(inserted_id="abc123"))

    fake_mdb = MagicMock()
    fake_mdb.__getitem__ = MagicMock(return_value=fake_coll)

    with (
        patch("app.services.memory.embed", new_callable=AsyncMock, return_value=fake_vec),
        patch("app.services.memory.get_mongo_db", new_callable=AsyncMock, return_value=fake_mdb),
    ):
        result = await store_memory(
            db, user_id=1, agent_id=42, fact="Python is great", visibility="private"
        )

    assert result["visibility"] == "private"
    assert "id" in result


# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_store_memory_private_requires_agent_id():
    """store_memory raises MemoryError for private visibility without agent_id."""
    db = _make_db()

    with pytest.raises(MemoryError, match="agent_id"):
        await store_memory(db, user_id=1, agent_id=None, fact="test", visibility="private")


# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_store_memory_invalid_visibility():
    """store_memory raises MemoryError for unknown visibility value."""
    db = _make_db()

    with pytest.raises(MemoryError, match="Invalid visibility"):
        await store_memory(db, user_id=1, agent_id=1, fact="test", visibility="unknown")


# ─────────────────────────────────────────────────────────────────────────────
# invalidate_mongo_client
# ─────────────────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
def test_invalidate_mongo_client_removes_cache():
    """invalidate_mongo_client removes and closes the cached client."""
    mock_client = MagicMock()
    _client_cache[9999] = (mock_client, "testdb")

    invalidate_mongo_client(9999)

    assert 9999 not in _client_cache
    mock_client.close.assert_called_once()


# [RCF:PROTECTED]
def test_invalidate_mongo_client_missing_key():
    """invalidate_mongo_client doesn't raise if user not in cache."""
    # Should not raise
    invalidate_mongo_client(99999999)


# ─────────────────────────────────────────────────────────────────────────────
# count_memories — returns 0 on error
# ─────────────────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_count_memories_returns_zero_on_error():
    """count_memories returns 0 when MongoDB is unreachable."""
    db = _make_db()

    with patch("app.services.memory.get_mongo_db", new_callable=AsyncMock, side_effect=Exception("no mongo")):
        result = await count_memories(db, user_id=1)

    assert result == 0


# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_count_memories_sums_collections():
    """count_memories sums private + shared document counts."""
    db = _make_db()

    private_coll = AsyncMock()
    private_coll.count_documents = AsyncMock(return_value=10)

    shared_coll = AsyncMock()
    shared_coll.count_documents = AsyncMock(return_value=5)

    call_count = [0]

# [RCF:PROTECTED]
    def getitem(key):
        call_count[0] += 1
        if "agent_memories" in key or call_count[0] == 1:
            return private_coll
        return shared_coll

    fake_mdb = MagicMock()
    # First call → private_coll, second → shared_coll
    fake_mdb.__getitem__ = MagicMock(side_effect=lambda k: private_coll if k == "agent_memories" else shared_coll)

    with patch("app.services.memory.get_mongo_db", new_callable=AsyncMock, return_value=fake_mdb):
        result = await count_memories(db, user_id=1)

    assert result == 15


# ─────────────────────────────────────────────────────────────────────────────
# build_shared_context_block
# ─────────────────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_build_shared_context_block_empty_query():
    """Returns empty string for empty or whitespace query."""
    db = _make_db()
    result = await build_shared_context_block(db, user_id=1, query="   ")
    assert result == ""


# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_build_shared_context_block_returns_empty_on_error():
    """Returns empty string if embed or mongo fails (best-effort injection)."""
    db = _make_db()

    with patch("app.services.memory.embed", new_callable=AsyncMock, side_effect=Exception("no embed")):
        result = await build_shared_context_block(db, user_id=1, query="something useful")

    assert result == ""


# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_build_shared_context_block_formats_facts():
    """Returns properly formatted XML block when facts are found."""
    db = _make_db()
    fake_vec = [0.0] * EMBED_DIM
    fake_results = [
        {"fact": "Python is a programming language", "tags": ["tech"], "score": 0.9},
        {"fact": "FastAPI is async", "tags": [], "score": 0.8},
    ]

    with (
        patch("app.services.memory.embed", new_callable=AsyncMock, return_value=fake_vec),
        patch("app.services.memory.get_mongo_db", new_callable=AsyncMock),
        patch("app.services.memory._vector_search", new_callable=AsyncMock, return_value=fake_results),
    ):
        result = await build_shared_context_block(db, user_id=1, query="what language?")

    assert "<shared_context>" in result
    assert "</shared_context>" in result
    assert "Python is a programming language" in result
    assert "[tech]" in result
    assert "FastAPI is async" in result


# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_build_shared_context_block_empty_results():
    """Returns empty string when no facts match."""
    db = _make_db()
    fake_vec = [0.0] * EMBED_DIM

    with (
        patch("app.services.memory.embed", new_callable=AsyncMock, return_value=fake_vec),
        patch("app.services.memory.get_mongo_db", new_callable=AsyncMock),
        patch("app.services.memory._vector_search", new_callable=AsyncMock, return_value=[]),
    ):
        result = await build_shared_context_block(db, user_id=1, query="something")

    assert result == ""
