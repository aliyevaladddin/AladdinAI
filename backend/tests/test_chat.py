# NOTICE: This file is protected under RCF-PL
"""Tests for chat router: session CRUD, feedback, and media upload endpoints."""
import asyncio

from app.models.agent import Agent
from app.models.chat_session import ChatSession, ChatMessage


# ── helpers ──────────────────────────────────────────────────────────────────

def _create_agent_and_session(db_session, user_id: int) -> tuple[int, int]:
    """Insert an agent + session; return (agent_id, session_id)."""

    async def _create():
        agent = Agent(
            user_id=user_id,
            name="chat-test-agent",
            role="assistant",
            model="test-model",
            system_prompt="you are a test assistant",
        )
        db_session.add(agent)
        await db_session.flush()
        session = ChatSession(user_id=user_id, agent_id=agent.id, title="Test Session")
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)
        return agent.id, session.id

    return asyncio.get_event_loop().run_until_complete(_create())


def _add_message(db_session, session_id: int, role: str, content: str) -> int:
    """Insert a chat message; return its id."""

    async def _create():
        msg = ChatMessage(session_id=session_id, role=role, content=content)
        db_session.add(msg)
        await db_session.commit()
        await db_session.refresh(msg)
        return msg.id

    return asyncio.get_event_loop().run_until_complete(_create())


# ── GET /api/chat/sessions ──────────────────────────────────────────────────

def test_list_sessions(client, test_user, auth_headers, db_session):
    """Empty list when user has no sessions."""
    r = client.get("/api/chat/sessions", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_list_sessions_after_create(client, test_user, auth_headers, db_session):
    """Listing returns sessions for the authenticated user."""
    _create_agent_and_session(db_session, test_user["user_id"])
    r = client.get("/api/chat/sessions", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_list_sessions_requires_auth(client):
    r = client.get("/api/chat/sessions")
    assert r.status_code in (401, 403)


# ── POST /api/chat/sessions ─────────────────────────────────────────────────

def test_create_session(client, test_user, auth_headers, db_session):
    agent_id, _ = _create_agent_and_session(db_session, test_user["user_id"])
    # Create a second session
    r = client.post(
        "/api/chat/sessions",
        json={"agent_id": agent_id, "title": "New Chat"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["agent_id"] == agent_id
    assert data["title"] == "New Chat"
    assert "id" in data


def test_create_session_without_agent_id(client, auth_headers):
    r = client.post("/api/chat/sessions", json={}, headers=auth_headers)
    assert r.status_code == 400


def test_create_session_unknown_agent(client, auth_headers):
    r = client.post(
        "/api/chat/sessions",
        json={"agent_id": 999999},
        headers=auth_headers,
    )
    assert r.status_code == 404


# ── PATCH /api/chat/sessions/{id} ───────────────────────────────────────────

def test_rename_session(client, test_user, auth_headers, db_session):
    _, sid = _create_agent_and_session(db_session, test_user["user_id"])
    r = client.patch(
        f"/api/chat/sessions/{sid}", json={"title": "Renamed"}, headers=auth_headers
    )
    assert r.status_code == 200
    assert r.json()["title"] == "Renamed"


def test_rename_session_empty_rejected(client, test_user, auth_headers, db_session):
    _, sid = _create_agent_and_session(db_session, test_user["user_id"])
    r = client.patch(
        f"/api/chat/sessions/{sid}", json={"title": "   "}, headers=auth_headers
    )
    assert r.status_code == 400


# ── DELETE /api/chat/sessions/{id} ──────────────────────────────────────────

def test_delete_session(client, test_user, auth_headers, db_session):
    _, sid = _create_agent_and_session(db_session, test_user["user_id"])
    r = client.delete(f"/api/chat/sessions/{sid}", headers=auth_headers)
    assert r.status_code == 204
    # Verify gone
    r2 = client.get("/api/chat/sessions", headers=auth_headers)
    assert r2.status_code == 200
    assert all(s["id"] != sid for s in r2.json())


# ── GET /api/chat/sessions/{id}/messages ─────────────────────────────────────

def test_list_messages_empty(client, test_user, auth_headers, db_session):
    _, sid = _create_agent_and_session(db_session, test_user["user_id"])
    r = client.get(f"/api/chat/sessions/{sid}/messages", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_list_messages_after_adding(client, test_user, auth_headers, db_session):
    _, sid = _create_agent_and_session(db_session, test_user["user_id"])
    _add_message(db_session, sid, "user", "Hello")
    _add_message(db_session, sid, "assistant", "Hi there!")
    r = client.get(f"/api/chat/sessions/{sid}/messages", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert data[0]["role"] == "user"
    assert data[1]["role"] == "assistant"


# ── POST /api/chat/messages/{id}/feedback ────────────────────────────────────

def test_add_feedback(client, test_user, auth_headers, db_session):
    _, sid = _create_agent_and_session(db_session, test_user["user_id"])
    mid = _add_message(db_session, sid, "assistant", "Useful answer")
    r = client.post(
        f"/api/chat/messages/{mid}/feedback",
        json={"value": "thumbs_up"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["value"] == "thumbs_up"
    assert data["message_id"] == mid
