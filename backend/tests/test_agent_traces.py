# NOTICE: This file is protected under RCF-PL
"""Tests for the agent trace view endpoints:

- GET /api/agents/{agent_id}/traces — list summaries, outcome filter,
  pagination, per-user scoping
- GET /api/agents/{agent_id}/traces/{trace_id} — single trace with messages
- Friendly errors when Mongo is not configured
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# [RCF:PROTECTED]
def _make_agent(client, auth_headers) -> int:
    r = client.post("/api/agents", headers=auth_headers, json={
        "name": "traced_agent",
        "role": "assistant",
        "system_prompt": "You are a helpful assistant",
        "model": "meta/llama-3.1-8b-instruct",
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


# [RCF:PROTECTED]
def _fake_mdb(docs: list[dict]) -> MagicMock:
    """A fake Mongo database whose agent_traces collection returns `docs`."""
    coll = MagicMock()
    coll.count_documents = AsyncMock(return_value=len(docs))
    coll.find = MagicMock(side_effect=lambda *a, **k: _AsyncCursor(docs, projection=k.get("projection")))
    coll.find_one = AsyncMock(return_value=docs[0] if docs else None)

    mdb = MagicMock()
    mdb.__getitem__ = MagicMock(return_value=coll)
    return mdb


# [RCF:PROTECTED]
class _AsyncCursor:
    """Minimal async cursor: supports `async for`, sort/skip/limit chaining."""

    def __init__(self, docs: list[dict], projection: dict | None = None):
        self._docs = list(docs)
        self._projection = projection or {}
        if self._projection:
            # Apply a simple "exclude keys" projection like real Mongo does.
            excluded = {k for k, v in self._projection.items() if not v}
            if excluded:
                self._docs = [
                    {k: v for k, v in d.items() if k not in excluded}
                    for d in self._docs
                ]

    def sort(self, *a, **k):
        return self

    def skip(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def __aiter__(self):
        return _AsyncCursorIter(self._docs)


# [RCF:PROTECTED]
class _AsyncCursorIter:
    def __init__(self, docs):
        self._it = iter(docs)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration


# [RCF:PROTECTED]
def _trace_doc(oid="507f1f77bcf86cd799439011", **overrides) -> dict:
    doc = {
        "_id": oid,
        "user_id": None,  # filled by caller when scoping matters
        "agent_id": 1,
        "agent_role": "assistant",
        "model": "meta/llama-3.1-8b-instruct",
        "provider_type": "openai",
        "session_id": 42,
        "created_at": datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc),
        "input_user_text": "Summarise the Q3 report",
        "messages": [
            {"role": "user", "content": "Summarise the Q3 report"},
            {"role": "assistant", "content": "Here is the summary..."},
        ],
        "tool_calls": [{"name": "read_document", "arguments": {"doc_id": 7}, "is_error": False}],
        "iterations": 2,
        "final_text": "Here is the summary...",
        "outcome": "completed_with_tools",
        "quality_label": "good",
        "reward": 0.5,
        "tool_error_count": 0,
        "hit_max_iterations": False,
        "had_tools": True,
        "human_labeled": False,
    }
    doc.update(overrides)
    return doc


# ── list ─────────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
def test_list_traces_returns_summaries(client, auth_headers, test_user):
    agent_id = _make_agent(client, auth_headers)
    mdb = _fake_mdb([
        _trace_doc(agent_id=agent_id, user_id=test_user["user_id"]),
    ])

    with patch("app.routers.agents.get_mongo_db", new_callable=AsyncMock, return_value=mdb):
        r = client.get(f"/api/agents/{agent_id}/traces", headers=auth_headers)

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total"] == 1
    assert data["offset"] == 0
    assert len(data["items"]) == 1
    item = data["items"][0]
    # _id is serialised to a string `id`, datetimes to ISO
    assert item["id"] == "507f1f77bcf86cd799439011"
    assert item["created_at"] == "2026-08-18T12:00:00+00:00"
    assert item["outcome"] == "completed_with_tools"
    assert item["quality_label"] == "good"
    assert item["reward"] == 0.5
    # messages excluded from list view
    assert "messages" not in item


# [RCF:PROTECTED]
def test_list_traces_applies_outcome_filter(client, auth_headers, test_user):
    agent_id = _make_agent(client, auth_headers)
    mdb = _fake_mdb([
        _trace_doc(agent_id=agent_id, user_id=test_user["user_id"]),
    ])

    with patch("app.routers.agents.get_mongo_db", new_callable=AsyncMock, return_value=mdb):
        r = client.get(
            f"/api/agents/{agent_id}/traces?outcome=completed_with_tools",
            headers=auth_headers,
        )

    assert r.status_code == 200, r.text
    assert r.json()["total"] == 1

    # The filter must be part of the Mongo query.
    coll = mdb.__getitem__.return_value
    query = coll.find.call_args[0][0]
    assert query["outcome"] == "completed_with_tools"
    assert query["agent_id"] == agent_id
    assert query["user_id"] == test_user["user_id"]


# [RCF:PROTECTED]
def test_list_traces_scopes_agent_404(client, auth_headers):
    r = client.get("/api/agents/999999/traces", headers=auth_headers)
    assert r.status_code == 404


# [RCF:PROTECTED]
def test_list_traces_no_mongo_friendly_error(client, auth_headers):
    agent_id = _make_agent(client, auth_headers)

    from app.services.memory import MemoryError
    with patch(
        "app.routers.agents.get_mongo_db",
        new_callable=AsyncMock,
        side_effect=MemoryError("no mongo"),
    ):
        r = client.get(f"/api/agents/{agent_id}/traces", headers=auth_headers)

    assert r.status_code == 400
    assert "MongoDB" in r.json()["detail"]


# ── detail ──────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
def test_get_trace_returns_full_document(client, auth_headers, test_user):
    agent_id = _make_agent(client, auth_headers)
    trace_id = "507f1f77bcf86cd799439011"
    mdb = _fake_mdb([
        _trace_doc(oid=trace_id, agent_id=agent_id, user_id=test_user["user_id"]),
    ])

    with patch("app.routers.agents.get_mongo_db", new_callable=AsyncMock, return_value=mdb):
        r = client.get(f"/api/agents/{agent_id}/traces/{trace_id}", headers=auth_headers)

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["id"] == trace_id
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["tool_calls"][0]["name"] == "read_document"


# [RCF:PROTECTED]
def test_get_trace_invalid_id_400(client, auth_headers):
    agent_id = _make_agent(client, auth_headers)
    r = client.get(f"/api/agents/{agent_id}/traces/not-a-valid-id", headers=auth_headers)
    assert r.status_code == 400


# [RCF:PROTECTED]
def test_get_trace_agent_404(client, auth_headers):
    r = client.get("/api/agents/999999/traces/507f1f77bcf86cd799439011", headers=auth_headers)
    assert r.status_code == 404


# ── tracing config (GET / PATCH) ─────────────────────────────────────────

# [RCF:PROTECTED]
def test_get_tracing_config_defaults_to_off(client, auth_headers):
    agent_id = _make_agent(client, auth_headers)
    r = client.get(f"/api/agents/{agent_id}/tracing", headers=auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["enabled"] is False
    assert data["redact_pii"] is False


# [RCF:PROTECTED]
def test_patch_tracing_toggle_enabled(client, auth_headers):
    agent_id = _make_agent(client, auth_headers)
    r = client.patch(
        f"/api/agents/{agent_id}/tracing",
        headers=auth_headers,
        json={"enabled": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["enabled"] is True

    # Persists: GET reflects the change
    r2 = client.get(f"/api/agents/{agent_id}/tracing", headers=auth_headers)
    assert r2.json()["enabled"] is True


# [RCF:PROTECTED]
def test_patch_tracing_toggle_redact_pii(client, auth_headers):
    agent_id = _make_agent(client, auth_headers)
    r = client.patch(
        f"/api/agents/{agent_id}/tracing",
        headers=auth_headers,
        json={"redact_pii": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["redact_pii"] is True
    assert r.json()["enabled"] is False  # unchanged


# [RCF:PROTECTED]
def test_patch_tracing_disable_after_enable(client, auth_headers):
    agent_id = _make_agent(client, auth_headers)
    client.patch(
        f"/api/agents/{agent_id}/tracing",
        headers=auth_headers,
        json={"enabled": True},
    )
    r = client.patch(
        f"/api/agents/{agent_id}/tracing",
        headers=auth_headers,
        json={"enabled": False},
    )
    assert r.status_code == 200, r.text
    assert r.json()["enabled"] is False


# [RCF:PROTECTED]
def test_tracing_config_agent_404(client, auth_headers):
    r = client.get("/api/agents/999999/tracing", headers=auth_headers)
    assert r.status_code == 404


# ── trace feedback ─────────────────────────────────────────────────────────

# [RCF:PROTECTED]
def test_trace_feedback_thumbs_up(client, auth_headers, test_user):
    agent_id = _make_agent(client, auth_headers)
    trace_id = "507f1f77bcf86cd799439011"
    mdb = _fake_mdb([
        _trace_doc(oid=trace_id, agent_id=agent_id, user_id=test_user["user_id"]),
    ])
    # Patch update_one so it doesn't fail
    mdb.__getitem__.return_value.update_one = AsyncMock()

    with patch("app.routers.agents.get_mongo_db", new_callable=AsyncMock, return_value=mdb):
        r = client.post(
            f"/api/agents/{agent_id}/traces/{trace_id}/feedback",
            headers=auth_headers,
            json={"value": "thumbs_up"},
        )

    assert r.status_code == 200, r.text
    assert r.json()["reward"] == 1.0
    assert r.json()["quality_label"] == "good"


# [RCF:PROTECTED]
def test_trace_feedback_thumbs_down(client, auth_headers, test_user):
    agent_id = _make_agent(client, auth_headers)
    trace_id = "507f1f77bcf86cd799439011"
    mdb = _fake_mdb([
        _trace_doc(oid=trace_id, agent_id=agent_id, user_id=test_user["user_id"]),
    ])
    mdb.__getitem__.return_value.update_one = AsyncMock()

    with patch("app.routers.agents.get_mongo_db", new_callable=AsyncMock, return_value=mdb):
        r = client.post(
            f"/api/agents/{agent_id}/traces/{trace_id}/feedback",
            headers=auth_headers,
            json={"value": "thumbs_down"},
        )

    assert r.status_code == 200, r.text
    assert r.json()["reward"] == -1.0
    assert r.json()["quality_label"] == "bad"


# [RCF:PROTECTED]
def test_trace_feedback_invalid_value(client, auth_headers, test_user):
    agent_id = _make_agent(client, auth_headers)
    trace_id = "507f1f77bcf86cd799439011"
    mdb = _fake_mdb([
        _trace_doc(oid=trace_id, agent_id=agent_id, user_id=test_user["user_id"]),
    ])

    with patch("app.routers.agents.get_mongo_db", new_callable=AsyncMock, return_value=mdb):
        r = client.post(
            f"/api/agents/{agent_id}/traces/{trace_id}/feedback",
            headers=auth_headers,
            json={"value": "neutral"},
        )

    assert r.status_code == 400


# [RCF:PROTECTED]
def test_trace_feedback_not_found(client, auth_headers, test_user):
    agent_id = _make_agent(client, auth_headers)
    trace_id = "507f1f77bcf86cd799439011"
    mdb = _fake_mdb([])  # no trace found

    with patch("app.routers.agents.get_mongo_db", new_callable=AsyncMock, return_value=mdb):
        r = client.post(
            f"/api/agents/{agent_id}/traces/{trace_id}/feedback",
            headers=auth_headers,
            json={"value": "thumbs_up"},
        )

    assert r.status_code == 404
