# NOTICE: This file is protected under RCF-PL
"""Tests for the global traces endpoint:

- GET /api/traces — list traces across all agents, agent filter, outcome filter,
  pagination, agent name enrichment
"""
from unittest.mock import AsyncMock, MagicMock, patch

from tests.test_agent_traces import _AsyncCursor, _trace_doc


def _make_agent(client, auth_headers, name="traced_agent") -> int:
    r = client.post("/api/agents", headers=auth_headers, json={
        "name": name,
        "role": "assistant",
        "system_prompt": "You are a helpful assistant",
        "model": "meta/llama-3.1-8b-instruct",
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _fake_mdb(docs):
    coll = MagicMock()
    coll.count_documents = AsyncMock(return_value=len(docs))
    coll.find = MagicMock(side_effect=lambda *a, **k: _AsyncCursor(docs, projection=k.get("projection")))
    mdb = MagicMock()
    mdb.__getitem__ = MagicMock(return_value=coll)
    return mdb


def test_list_all_traces_returns_items(client, auth_headers, test_user):
    agent_id = _make_agent(client, auth_headers)
    docs = [_trace_doc(agent_id=agent_id, user_id=test_user["user_id"])]
    mdb = _fake_mdb(docs)

    with patch("app.routers.traces.get_mongo_db", new_callable=AsyncMock, return_value=mdb):
        r = client.get("/api/traces", headers=auth_headers)

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["agent_name"] == "traced_agent"
    assert "messages" not in item  # summary projection


def test_list_all_traces_filters_by_agent(client, auth_headers, test_user):
    a1 = _make_agent(client, auth_headers, "agent_one")
    a2 = _make_agent(client, auth_headers, "agent_two")
    docs = [
        _trace_doc(agent_id=a1, user_id=test_user["user_id"]),
        _trace_doc(agent_id=a2, user_id=test_user["user_id"]),
    ]
    mdb = _fake_mdb(docs)

    with patch("app.routers.traces.get_mongo_db", new_callable=AsyncMock, return_value=mdb):
        r = client.get(f"/api/traces?agent_id={a2}", headers=auth_headers)

    assert r.status_code == 200, r.text
    coll = mdb.__getitem__.return_value
    query = coll.find.call_args[0][0]
    assert query["agent_id"] == a2


def test_list_all_traces_filters_by_outcome(client, auth_headers, test_user):
    agent_id = _make_agent(client, auth_headers)
    mdb = _fake_mdb([_trace_doc(agent_id=agent_id, user_id=test_user["user_id"])])

    with patch("app.routers.traces.get_mongo_db", new_callable=AsyncMock, return_value=mdb):
        r = client.get("/api/traces?outcome=completed_with_tools", headers=auth_headers)

    assert r.status_code == 200, r.text
    coll = mdb.__getitem__.return_value
    query = coll.find.call_args[0][0]
    assert query["outcome"] == "completed_with_tools"


def test_list_all_traces_no_agents_returns_empty(client, auth_headers):
    """No agents → no traces to query."""
    with patch("app.routers.traces.get_mongo_db", new_callable=AsyncMock):
        r = client.get("/api/traces", headers=auth_headers)

    assert r.status_code == 200, r.text
    assert r.json()["total"] == 0


def test_list_all_traces_no_mongo_friendly_error(client, auth_headers):
    _make_agent(client, auth_headers)
    from app.services.memory import MemoryError

    with patch(
        "app.routers.traces.get_mongo_db",
        new_callable=AsyncMock,
        side_effect=MemoryError("no mongo"),
    ):
        r = client.get("/api/traces", headers=auth_headers)

    assert r.status_code == 400
    assert "MongoDB" in r.json()["detail"]


def test_list_all_traces_agent_404(client, auth_headers):
    _make_agent(client, auth_headers)
    from app.services.memory import MemoryError

    with patch(
        "app.routers.traces.get_mongo_db",
        new_callable=AsyncMock,
        side_effect=MemoryError("no mongo"),
    ):
        r = client.get("/api/traces?agent_id=999999", headers=auth_headers)

    assert r.status_code in (400, 404)
