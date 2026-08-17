# NOTICE: This file is protected under RCF-PL
"""Tests for chat session naming: auto-title helper + PATCH rename endpoint."""
import asyncio
import uuid

from app.models.agent import Agent
from app.models.chat_session import ChatSession
from app.routers.chat import _auto_session_title


# ── _auto_session_title (pure) ─────────────────────────────────────────────
def test_auto_title_from_text():
    assert _auto_session_title("hello there", None) == "hello there"


def test_auto_title_truncates_long_text():
    assert _auto_session_title("x" * 120, None) == "x" * 60 + "..."


def test_auto_title_whitespace_only_falls_back():
    assert _auto_session_title("   ", None) == "New Chat"


def test_auto_title_audio_fallback():
    atts = [{"filename": "v.webm", "mime": "audio/webm", "kind": "audio"}]
    assert _auto_session_title("", atts) == "Voice message"


def test_auto_title_image_fallback():
    atts = [{"filename": "p.png", "mime": "image/png", "kind": "image"}]
    assert _auto_session_title("", atts) == "Image"


def test_auto_title_generic_attachment_fallback():
    atts = [{"filename": "r.pdf", "mime": "application/pdf", "kind": "document"}]
    assert _auto_session_title("", atts) == "Attachment"


def test_auto_title_text_beats_attachments():
    atts = [{"filename": "p.png", "mime": "image/png"}]
    assert _auto_session_title("look at this", atts) == "look at this"


# ── PATCH /chat/sessions/{id} ──────────────────────────────────────────────
def _make_session(db_session, user_id: int) -> int:
    """Insert an agent + session directly; return the session id."""

    async def _create():
        agent = Agent(
            user_id=user_id, name="chat-test", role="assistant",
            model="x", system_prompt="you are a test",
        )
        db_session.add(agent)
        await db_session.flush()
        session = ChatSession(user_id=user_id, agent_id=agent.id, title="Old title")
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)
        return session.id

    return asyncio.get_event_loop().run_until_complete(_create())


def test_rename_session(client, test_user, auth_headers, db_session):
    sid = _make_session(db_session, test_user["user_id"])
    r = client.patch(
        f"/api/chat/sessions/{sid}", json={"title": "New title"}, headers=auth_headers
    )
    assert r.status_code == 200
    assert r.json()["title"] == "New title"


def test_rename_session_strips_whitespace(client, test_user, auth_headers, db_session):
    sid = _make_session(db_session, test_user["user_id"])
    r = client.patch(
        f"/api/chat/sessions/{sid}", json={"title": "  Padded  "}, headers=auth_headers
    )
    assert r.status_code == 200
    assert r.json()["title"] == "Padded"


def test_rename_session_empty_title_rejected(client, test_user, auth_headers, db_session):
    sid = _make_session(db_session, test_user["user_id"])
    r = client.patch(
        f"/api/chat/sessions/{sid}", json={"title": "   "}, headers=auth_headers
    )
    assert r.status_code == 400


def test_rename_session_missing_title_rejected(client, test_user, auth_headers, db_session):
    sid = _make_session(db_session, test_user["user_id"])
    r = client.patch(f"/api/chat/sessions/{sid}", json={}, headers=auth_headers)
    assert r.status_code == 400


def test_rename_session_requires_auth(client, test_user, db_session):
    sid = _make_session(db_session, test_user["user_id"])
    r = client.patch(f"/api/chat/sessions/{sid}", json={"title": "x"})
    assert r.status_code in (401, 403)


def test_rename_foreign_session_returns_404(client, test_user, auth_headers, db_session):
    sid = _make_session(db_session, test_user["user_id"])
    email = f"other-{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post(
        "/api/auth/register",
        json={"email": email, "password": "testpassword123", "name": "Other"},
    )
    assert reg.status_code == 201
    other_headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    r = client.patch(
        f"/api/chat/sessions/{sid}", json={"title": "hijacked"}, headers=other_headers
    )
    assert r.status_code == 404
    # Owner's title is untouched.
    own = client.get("/api/chat/sessions", headers=auth_headers)
    assert own.status_code == 200
    titles = {s["id"]: s["title"] for s in own.json()}
    assert titles[sid] == "Old title"
