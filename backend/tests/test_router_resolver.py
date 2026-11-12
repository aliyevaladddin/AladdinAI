# NOTICE: This file is protected under RCF-PL
"""Tests for router_resolver service.

Verifies:
1. Keyword match successfully routes to designated agent.
2. When no keyword matches and a channel_agent_id is present, the router does NOT
   hijack the channel with fallback_agent_id (channel agent is preserved).
3. When no channel_agent_id exists, fallback_agent_id is returned.
4. Empty text returns None without hitting database queries.
"""
import pytest
from app.models.router_config import RouterConfig
from app.services.router_resolver import resolve_agent_id


@pytest.mark.asyncio
async def test_router_preserves_channel_agent_when_no_rule_matches(test_user, db_session):
    uid = test_user["user_id"]

    # Active router config with keyword rule and a fallback agent 99
    cfg = RouterConfig(
        user_id=uid,
        name="Sales Keyword Router",
        type="keyword",
        config={
            "rules": [
                {"keywords": ["pricing", "quote"], "agent_id": 5},
            ],
            "fallback_agent_id": 99,
        },
        is_active=True,
    )
    db_session.add(cfg)
    await db_session.commit()

    # Message with non-matching text from a channel assigned to Agent 13
    routed = await resolve_agent_id(
        db_session, uid, "Hello, how are you?", channel_agent_id=13
    )

    # Must be None so caller keeps channel_agent_id (13), rather than hijacking to 99!
    assert routed is None


@pytest.mark.asyncio
async def test_router_overrides_when_rule_matches(test_user, db_session):
    uid = test_user["user_id"]

    cfg = RouterConfig(
        user_id=uid,
        name="Sales Keyword Router",
        type="keyword",
        config={
            "rules": [
                {"keywords": ["pricing", "quote"], "agent_id": 5},
            ],
            "fallback_agent_id": 99,
        },
        is_active=True,
    )
    db_session.add(cfg)
    await db_session.commit()

    # Matching message should route to Agent 5 even if channel has Agent 13
    routed = await resolve_agent_id(
        db_session, uid, "Please send me pricing details", channel_agent_id=13
    )
    assert routed == 5


@pytest.mark.asyncio
async def test_router_uses_fallback_when_no_channel_agent(test_user, db_session):
    uid = test_user["user_id"]

    cfg = RouterConfig(
        user_id=uid,
        name="Global Router",
        type="keyword",
        config={
            "rules": [
                {"keywords": ["billing"], "agent_id": 2},
            ],
            "fallback_agent_id": 42,
        },
        is_active=True,
    )
    db_session.add(cfg)
    await db_session.commit()

    # When channel has no agent assigned (channel_agent_id=None), fallback applies
    routed = await resolve_agent_id(
        db_session, uid, "General inquiry without keywords", channel_agent_id=None
    )
    assert routed == 42


@pytest.mark.asyncio
async def test_router_empty_text_returns_none(db_session):
    routed = await resolve_agent_id(db_session, 1, "", channel_agent_id=10)
    assert routed is None
