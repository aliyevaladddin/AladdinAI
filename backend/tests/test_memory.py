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
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DOCUMENT_COLLECTION,
    EMBED_DIM,
    VECTOR_INDEX_FILTERS,
    VECTOR_INDEX_NAME,
    MemoryError,
    _client_cache,
    build_shared_context_block,
    chunk_text_content,
    count_memories,
    embed,
    ensure_vector_indexes,
    invalidate_mongo_client,
    store_document_chunk,
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
    provider.embedding_model = "nvidia/nv-embedqa-e5-v5"

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
    provider.embedding_model = "nvidia/nv-embedqa-e5-v5"

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


# ─────────────────────────────────────────────────────────────────────────────
# Documents are not facts
# ─────────────────────────────────────────────────────────────────────────────


# [RCF:PROTECTED]
def test_chunk_prose_overlaps():
    """Prose is split on character count, with each chunk overlapping the last."""
    text = "".join(str(i % 10) for i in range(2500))
    chunks = chunk_text_content(text, tabular=False)

    assert len(chunks) > 1
    assert all(len(c) <= CHUNK_SIZE for c in chunks)
    # The tail of one chunk reappears at the head of the next.
    assert chunks[1].startswith(chunks[0][-CHUNK_OVERLAP:])
    # Nothing is lost.
    assert chunks[0][0] == text[0]
    assert text.endswith(chunks[-1][-10:])


# [RCF:PROTECTED]
def test_chunk_table_repeats_header():
    """Every chunk of a table carries the header, so no chunk is unlabelled.

    This is the defect that produced `Total before Taxes NaN NaN NaN 34980` —
    a row severed from its column names, mid-table.
    """
    header = "item,hours,rate,total"
    rows = [f"task-{i},{i},100,{i * 100}" for i in range(200)]
    table = "\n".join([header, *rows])

    chunks = chunk_text_content(table, tabular=True)

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.startswith(header)
        # Rows are never cut in half.
        for line in chunk.splitlines():
            assert line.count(",") == header.count(",")

    # Every data row survives exactly once.
    seen = [
        line
        for chunk in chunks
        for line in chunk.splitlines()[1:]
    ]
    assert seen == rows


# [RCF:PROTECTED]
def test_chunk_table_header_only():
    """A header with no rows is still indexed rather than dropped."""
    assert chunk_text_content("a,b,c", tabular=True) == ["a,b,c"]


# [RCF:PROTECTED]
def test_chunk_empty_text():
    """Empty input yields no chunks, in both modes."""
    assert chunk_text_content("", tabular=False) == []
    assert chunk_text_content("   \n  ", tabular=True) == []


# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_shared_context_excludes_legacy_file_chunks():
    """Document chunks must never reach a system prompt.

    Legacy uploads live in `shared_context` tagged `file-upload`. Injecting them
    is what put 29 slices of one spreadsheet in front of every agent.
    """
    db = _make_db()
    fake_vec = [0.0] * EMBED_DIM
    fake_results = [
        {
            "fact": "Content from uploaded file 'q.xlsx' (part 28/29):\nAwards NaN NaN 2.0",
            "tags": ["file-upload", "q.xlsx"],
            "score": 0.95,
        },
        {"fact": "Acme renewed in March", "tags": ["crm"], "score": 0.7},
    ]

    with (
        patch("app.services.memory.embed", new_callable=AsyncMock, return_value=fake_vec),
        patch("app.services.memory.get_mongo_db", new_callable=AsyncMock),
        patch("app.services.memory._vector_search", new_callable=AsyncMock, return_value=fake_results),
    ):
        result = await build_shared_context_block(db, user_id=1, query="renewals")

    assert "Acme renewed in March" in result
    assert "file-upload" not in result
    assert "NaN" not in result


# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_shared_context_empty_when_only_file_chunks():
    """If every hit is a document chunk, the block is empty — not a table dump."""
    db = _make_db()
    fake_vec = [0.0] * EMBED_DIM
    fake_results = [
        {"fact": f"chunk {i}", "tags": ["file-upload"], "score": 0.9} for i in range(5)
    ]

    with (
        patch("app.services.memory.embed", new_callable=AsyncMock, return_value=fake_vec),
        patch("app.services.memory.get_mongo_db", new_callable=AsyncMock),
        patch("app.services.memory._vector_search", new_callable=AsyncMock, return_value=fake_results),
    ):
        result = await build_shared_context_block(db, user_id=1, query="anything")

    assert result == ""


# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_store_document_chunk_writes_to_document_collection():
    """Document chunks go to their own collection, with no `fact` field."""
    db = _make_db()
    fake_vec = [0.0] * EMBED_DIM

    coll = MagicMock()
    coll.insert_one = AsyncMock(return_value=MagicMock(inserted_id="abc123"))
    mdb = MagicMock()
    mdb.__getitem__ = MagicMock(return_value=coll)

    with (
        patch("app.services.memory.embed", new_callable=AsyncMock, return_value=fake_vec),
        patch("app.services.memory.get_mongo_db", new_callable=AsyncMock, return_value=mdb),
    ):
        out = await store_document_chunk(
            db, user_id=1, filename="q.xlsx", text="item,total\nawards,34980", part=1, total_parts=3
        )

    mdb.__getitem__.assert_called_with(DOCUMENT_COLLECTION)
    doc = coll.insert_one.call_args[0][0]
    assert doc["filename"] == "q.xlsx"
    assert doc["text"] == "item,total\nawards,34980"
    assert doc["part"] == 1 and doc["total_parts"] == 3
    assert "fact" not in doc
    assert "visibility" not in doc
    assert out["id"] == "abc123"


# ─────────────────────────────────────────────────────────────────────────────
# ensure_vector_indexes() — provisioning
# ─────────────────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
def _make_mdb(*, collections: list[str], indexes: dict[str, list[str]]):
    """Fake Atlas database whose collections report the given search indexes."""
    colls: dict[str, MagicMock] = {}

    for name in VECTOR_INDEX_FILTERS:
        coll = MagicMock()
        coll.create_search_index = AsyncMock(return_value=VECTOR_INDEX_NAME)

        async def _list(_names=indexes.get(name, [])):
            for n in _names:
                yield {"name": n}

        coll.list_search_indexes = MagicMock(side_effect=lambda _l=_list: _l())
        colls[name] = coll

    mdb = MagicMock()
    mdb.list_collection_names = AsyncMock(return_value=collections)
    mdb.create_collection = AsyncMock()
    mdb.__getitem__ = MagicMock(side_effect=lambda n: colls[n])
    return mdb, colls


# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_ensure_vector_indexes_creates_missing_document_index():
    """The document index is created, and its filter matches how it is queried.

    `search_documents` filters on `user_id`; a filter path absent from the index
    makes Atlas reject the whole query, dropping it to the recency fallback.
    """
    db = _make_db()
    mdb, colls = _make_mdb(
        collections=["agent_memories", "shared_context", "document_chunks"],
        indexes={
            "agent_memories": [VECTOR_INDEX_NAME],
            "shared_context": [VECTOR_INDEX_NAME],
            "document_chunks": [],
        },
    )

    with patch("app.services.memory.get_mongo_db", new_callable=AsyncMock, return_value=mdb):
        out = await ensure_vector_indexes(db, 1)

    assert out[DOCUMENT_COLLECTION]["status"] == "created"
    assert out["agent_memories"]["status"] == "exists"
    assert out["shared_context"]["status"] == "exists"

    # Existing indexes are left alone — never recreated or redefined.
    colls["agent_memories"].create_search_index.assert_not_called()
    colls["shared_context"].create_search_index.assert_not_called()

    model = colls[DOCUMENT_COLLECTION].create_search_index.call_args[0][0]
    assert model["name"] == VECTOR_INDEX_NAME
    assert model["type"] == "vectorSearch"
    fields = model["definition"]["fields"]
    vector = next(f for f in fields if f["type"] == "vector")
    assert vector["path"] == "embedding"
    assert vector["numDimensions"] == EMBED_DIM
    assert vector["similarity"] == "cosine"
    assert {f["path"] for f in fields if f["type"] == "filter"} == {"user_id"}


# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_ensure_vector_indexes_creates_absent_collection_first():
    """createSearchIndexes fails on a namespace that does not exist yet.

    `document_chunks` only appears on first upload, so provisioning has to make
    the collection before indexing it.
    """
    db = _make_db()
    mdb, colls = _make_mdb(
        collections=["agent_memories", "shared_context"],
        indexes={"agent_memories": [VECTOR_INDEX_NAME], "shared_context": [VECTOR_INDEX_NAME]},
    )

    with patch("app.services.memory.get_mongo_db", new_callable=AsyncMock, return_value=mdb):
        out = await ensure_vector_indexes(db, 1)

    mdb.create_collection.assert_awaited_once_with(DOCUMENT_COLLECTION)
    assert out[DOCUMENT_COLLECTION]["collection_created"] is True
    assert out[DOCUMENT_COLLECTION]["status"] == "created"


# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_ensure_vector_indexes_is_idempotent():
    """Called twice against a provisioned cluster, it creates nothing."""
    db = _make_db()
    mdb, colls = _make_mdb(
        collections=list(VECTOR_INDEX_FILTERS),
        indexes={name: [VECTOR_INDEX_NAME] for name in VECTOR_INDEX_FILTERS},
    )

    with patch("app.services.memory.get_mongo_db", new_callable=AsyncMock, return_value=mdb):
        first = await ensure_vector_indexes(db, 1)
        second = await ensure_vector_indexes(db, 1)

    assert all(e["status"] == "exists" for e in first.values())
    assert first == second
    for coll in colls.values():
        coll.create_search_index.assert_not_called()
    mdb.create_collection.assert_not_awaited()


# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_ensure_vector_indexes_reports_non_atlas_cluster():
    """Self-hosted MongoDB has no Atlas Search: report it, don't raise.

    Everything else in memory still works there, so a missing search feature
    must not fail the connection test that calls this.
    """
    db = _make_db()
    mdb, colls = _make_mdb(
        collections=list(VECTOR_INDEX_FILTERS),
        indexes={name: [] for name in VECTOR_INDEX_FILTERS},
    )
    for coll in colls.values():
        coll.create_search_index = AsyncMock(
            side_effect=Exception("Search index commands are not supported on this deployment")
        )

    with patch("app.services.memory.get_mongo_db", new_callable=AsyncMock, return_value=mdb):
        out = await ensure_vector_indexes(db, 1)

    assert all(e["status"] == "unsupported" for e in out.values())
    assert "not supported" in out[DOCUMENT_COLLECTION]["detail"]


# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_ensure_vector_indexes_isolates_per_collection_failure():
    """One collection failing must not stop the others being provisioned."""
    db = _make_db()
    mdb, colls = _make_mdb(
        collections=list(VECTOR_INDEX_FILTERS),
        indexes={name: [] for name in VECTOR_INDEX_FILTERS},
    )
    colls["agent_memories"].create_search_index = AsyncMock(
        side_effect=Exception("quota exceeded")
    )

    with patch("app.services.memory.get_mongo_db", new_callable=AsyncMock, return_value=mdb):
        out = await ensure_vector_indexes(db, 1)

    assert out["agent_memories"]["status"] == "error"
    assert out[DOCUMENT_COLLECTION]["status"] == "created"
    assert out["shared_context"]["status"] == "created"
