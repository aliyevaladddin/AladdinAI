# NOTICE: This file is protected under RCF-PL
"""Tests for the human-feedback labeling layer.

Two levels:
  * pure mapping — `human_score` maps 👍/👎 to (reward, quality_label) with no DB;
  * the endpoint — ownership checks, upsert-flip, and validation.

The Mongo mirror (`schedule_feedback_update`) is fire-and-forget and depends on
a per-user Mongo connection that tests don't configure; it no-ops safely, so the
endpoint tests assert only the durable Postgres side.
"""
import asyncio

from app.services.tracing import human_score
from app.models.chat_session import ChatSession, ChatMessage
from app.models.message_feedback import MessageFeedback
from sqlalchemy import select


# ── pure mapping ───────────────────────────────────────────────────────────
def test_human_score_thumbs_up():
    assert human_score("thumbs_up") == (1.0, "good")


def test_human_score_thumbs_down():
    assert human_score("thumbs_down") == (-1.0, "bad")


def test_human_score_unknown_is_none():
    # Unknown value → no guess; caller treats as "no human label".
    assert human_score("shrug") == (None, None)


# ── endpoint ───────────────────────────────────────────────────────────────
def _make_assistant_message(db_session, user_id: int) -> tuple[int, int]:
    """Insert a session + one assistant message directly; return (msg_id, session_id)."""
    async def _create():
        # A test user has no agent; agent_id FK is nullable-tolerant on sqlite,
        # but chat_sessions.agent_id is NOT NULL — reuse user_id as a stand-in id
        # is unsafe, so create a minimal agent row instead.
        from app.models.agent import Agent
        agent = Agent(user_id=user_id, name="fb-test", role="assistant", model="x", system_prompt="you are a test")
        db_session.add(agent)
        await db_session.flush()
        session = ChatSession(user_id=user_id, agent_id=agent.id, title="t")
        db_session.add(session)
        await db_session.flush()
        msg = ChatMessage(session_id=session.id, role="assistant", content="hi", model="x")
        db_session.add(msg)
        await db_session.commit()
        await db_session.refresh(msg)
        return msg.id, session.id
    return asyncio.get_event_loop().run_until_complete(_create())


def test_feedback_thumbs_up_persists(client, test_user, auth_headers, db_session):
    msg_id, _ = _make_assistant_message(db_session, test_user["user_id"])
    r = client.post(
        f"/api/chat/messages/{msg_id}/feedback",
        json={"value": "thumbs_up"},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"message_id": msg_id, "value": "thumbs_up"}

    rows = asyncio.get_event_loop().run_until_complete(
        db_session.execute(select(MessageFeedback).where(MessageFeedback.message_id == msg_id))
    )
    fb = rows.scalars().all()
    assert len(fb) == 1 and fb[0].value == "thumbs_up"


def test_feedback_flip_updates_same_row(client, test_user, auth_headers, db_session):
    msg_id, _ = _make_assistant_message(db_session, test_user["user_id"])
    client.post(f"/api/chat/messages/{msg_id}/feedback", json={"value": "thumbs_up"}, headers=auth_headers)
    client.post(f"/api/chat/messages/{msg_id}/feedback", json={"value": "thumbs_down"}, headers=auth_headers)

    rows = asyncio.get_event_loop().run_until_complete(
        db_session.execute(select(MessageFeedback).where(MessageFeedback.message_id == msg_id))
    )
    fb = rows.scalars().all()
    assert len(fb) == 1, "re-clicking must flip, not stack duplicates"
    assert fb[0].value == "thumbs_down"


def test_feedback_invalid_value_rejected(client, test_user, auth_headers, db_session):
    msg_id, _ = _make_assistant_message(db_session, test_user["user_id"])
    r = client.post(
        f"/api/chat/messages/{msg_id}/feedback",
        json={"value": "meh"},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_feedback_unknown_message_404(client, test_user, auth_headers):
    r = client.post(
        "/api/chat/messages/999999/feedback",
        json={"value": "thumbs_up"},
        headers=auth_headers,
    )
    assert r.status_code == 404


def test_feedback_requires_auth(client, test_user, db_session):
    msg_id, _ = _make_assistant_message(db_session, test_user["user_id"])
    r = client.post(f"/api/chat/messages/{msg_id}/feedback", json={"value": "thumbs_up"})
    assert r.status_code == 401
