# NOTICE: This file is protected under RCF-PL
"""Tests for outgoing webhooks: CRUD + partial update, test-delivery endpoint,
event fan-out, unsigned (Zapier-style) delivery, RCF-signed delivery,
contact_created wiring, and the agent tools list_webhooks / send_webhook.
"""
import asyncio

import pytest

from conftest import TestingSessionLocal

from app.crypto import encrypt
from app.models.outgoing_webhook import OutgoingWebhook
from app.services import webhook_service
from app.tools.base import ToolContext, execute


# ── HTTP CRUD ────────────────────────────────────────────────────────────────
def test_create_and_list_webhook(client, auth_headers):
    r = client.post("/api/webhooks/outgoing", headers=auth_headers, json={
        "name": "My Zapier Hook",
        "url": "https://hooks.zapier.com/hooks/catch/123/abc/",
        "events": ["contact_created", "order_created"],
        "is_active": True,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["name"] == "My Zapier Hook"
    assert data["events"] == ["contact_created", "order_created"]

    hooks = client.get("/api/webhooks/outgoing", headers=auth_headers).json()
    assert len(hooks) == 1
    assert hooks[0]["url"].startswith("https://hooks.zapier.com/")


def test_delete_webhook(client, auth_headers):
    wid = client.post("/api/webhooks/outgoing", headers=auth_headers,
                      json={"name": "Doomed", "url": "https://example.com/h", "events": []}).json()["id"]
    assert client.delete(f"/api/webhooks/outgoing/{wid}", headers=auth_headers).status_code == 204
    assert client.get("/api/webhooks/outgoing", headers=auth_headers).json() == []


def test_webhook_scoping(client, test_user):
    u2 = client.post("/api/auth/register",
                     json={"email": "hook2@example.com", "password": "password123", "name": "U2"})
    h2 = {"Authorization": f"Bearer {u2.json()['access_token']}"}
    h1 = {"Authorization": f"Bearer {test_user['token']}"}
    client.post("/api/webhooks/outgoing", headers=h1,
                json={"name": "private", "url": "https://example.com/hook", "events": []})
    assert client.get("/api/webhooks/outgoing", headers=h2).json() == []


# ── HTTP update + test delivery ──────────────────────────────────────────────
def test_update_webhook_fields_and_secret_rotation(client, test_user, db_session, auth_headers):
    wid = client.post("/api/webhooks/outgoing", headers=auth_headers,
                      json={"name": "Old", "url": "https://example.com/a",
                            "events": ["deal_created"], "secret": "first"}).json()["id"]

    # Partial update: rename + swap events; omit secret → it must be kept.
    r = client.put(f"/api/webhooks/outgoing/{wid}", headers=auth_headers,
                   json={"name": "New", "events": ["order_created"]})
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "New"
    assert r.json()["events"] == ["order_created"]
    assert r.json()["url"] == "https://example.com/a"

    from app.crypto import decrypt
    hook = asyncio.get_event_loop().run_until_complete(db_session.get(OutgoingWebhook, wid))
    assert decrypt(hook.secret) == "first"  # unchanged

    # Rotate the secret.
    client.put(f"/api/webhooks/outgoing/{wid}", headers=auth_headers, json={"secret": "second"})
    hook = asyncio.get_event_loop().run_until_complete(db_session.get(OutgoingWebhook, wid))
    asyncio.get_event_loop().run_until_complete(db_session.refresh(hook))
    assert decrypt(hook.secret) == "second"

    # Empty secret → delivered unsigned from now on.
    client.put(f"/api/webhooks/outgoing/{wid}", headers=auth_headers, json={"secret": ""})
    asyncio.get_event_loop().run_until_complete(db_session.refresh(hook))
    assert hook.secret is None


def test_update_and_test_endpoints_are_scoped(client, test_user):
    other = client.post("/api/auth/register",
                        json={"email": "upd-other@example.com", "password": "password123", "name": "O"})
    oh = {"Authorization": f"Bearer {other.json()['access_token']}"}
    mine = {"Authorization": f"Bearer {test_user['token']}"}
    wid = client.post("/api/webhooks/outgoing", headers=mine,
                      json={"name": "Mine", "url": "https://example.com/m", "events": []}).json()["id"]

    assert client.put(f"/api/webhooks/outgoing/{wid}", headers=oh, json={"name": "Hijack"}).status_code == 404
    assert client.post(f"/api/webhooks/outgoing/{wid}/test", headers=oh).status_code == 404


def test_test_endpoint_delivers_event(client, auth_headers, captured_posts):
    wid = client.post("/api/webhooks/outgoing", headers=auth_headers,
                      json={"name": "Zap", "url": "https://hooks.zapier.com/hooks/catch/77/",
                            "events": []}).json()["id"]

    r = client.post(f"/api/webhooks/outgoing/{wid}/test", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True, "signed": False}

    assert len(captured_posts) == 1
    post = captured_posts[0]
    assert post["url"].startswith("https://hooks.zapier.com/")
    assert '"event": "test"' in post["content"]
    assert "Test event from AladdinAI" in post["content"]


def test_test_endpoint_reports_delivery_failure(client, auth_headers, monkeypatch):
    wid = client.post("/api/webhooks/outgoing", headers=auth_headers,
                      json={"name": "Dead", "url": "https://example.com/dead", "events": []}).json()["id"]

    async def fail_post(self, url, **kw):
        class R:
            status_code = 404
        return R()

    monkeypatch.setattr("httpx.AsyncClient.post", fail_post)
    r = client.post(f"/api/webhooks/outgoing/{wid}/test", headers=auth_headers)
    assert r.status_code == 502


# ── delivery ─────────────────────────────────────────────────────────────────
class _FakeResp:
    status_code = 200


@pytest.fixture
def captured_posts(monkeypatch):
    """Capture every httpx POST the webhook service makes, and point the
    service's own DB sessions at the test database (it uses the module-level
    app.database.async_session, which the TestClient override does not cover).
    Safe here because delivery tests drive the service sequentially via
    run_until_complete, never concurrently with an in-flight request session."""
    posts: list[dict] = []

    async def fake_post(self, url, content=None, headers=None, **kw):
        posts.append({"url": url, "content": content, "headers": headers or {}})
        return _FakeResp()

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    monkeypatch.setattr(webhook_service, "async_session", TestingSessionLocal)
    return posts


async def _mk_hook(db, user_id, events, secret=None, name="hook", active=True) -> OutgoingWebhook:
    w = OutgoingWebhook(
        user_id=user_id, name=name, url="https://hooks.zapier.com/hooks/catch/1/",
        secret=encrypt(secret) if secret else None, events=events, is_active=active,
    )
    db.add(w)
    await db.commit()
    await db.refresh(w)
    return w


def test_unsigned_webhook_delivers_without_rcf_headers(client, test_user, db_session, captured_posts):
    """Zapier-style hooks have no secret — they must still receive events,
    simply without RCF signature headers."""
    hook_id = client.post("/api/webhooks/outgoing",
                          headers={"Authorization": f"Bearer {test_user['token']}"},
                          json={"name": "zap", "url": "https://hooks.zapier.com/hooks/catch/1/",
                                "events": ["contact_created"]}).json()["id"]

    asyncio.get_event_loop().run_until_complete(
        webhook_service.trigger_webhooks(test_user["user_id"], "contact_created", {"contact_id": 7})
    )

    assert len(captured_posts) == 1
    post = captured_posts[0]
    assert post["url"].startswith("https://hooks.zapier.com/")
    assert "X-RCF-Marker" not in post["headers"]
    assert '"event": "contact_created"' in post["content"]
    assert '"contact_id": 7' in post["content"]

    # Unsigned delivery carries no chain — last_marker must stay null.
    hook = asyncio.get_event_loop().run_until_complete(db_session.get(OutgoingWebhook, hook_id))
    assert hook.last_marker is None


def test_signed_webhook_sets_marker_and_advances_chain(test_user, db_session, captured_posts):
    w = asyncio.get_event_loop().run_until_complete(
        _mk_hook(db_session, test_user["user_id"], ["deal_created"], secret="s3cret"))

    asyncio.get_event_loop().run_until_complete(
        webhook_service.trigger_webhooks(test_user["user_id"], "deal_created", {"deal_id": 1})
    )

    assert len(captured_posts) == 1
    headers = captured_posts[0]["headers"]
    assert headers.get("X-RCF-Marker")
    assert headers.get("X-RCF-Correlation-ID")
    assert headers.get("X-RCF-Timestamp")
    assert "X-RCF-Chain-Root" not in headers  # first delivery — no previous marker

    # The chain advanced in a separate session; refresh before asserting.
    asyncio.get_event_loop().run_until_complete(db_session.refresh(w))
    assert w.last_marker == headers["X-RCF-Marker"]

    # Second delivery chains off the first marker.
    asyncio.get_event_loop().run_until_complete(
        webhook_service.trigger_webhooks(test_user["user_id"], "deal_created", {"deal_id": 2})
    )
    assert len(captured_posts) == 2
    assert captured_posts[1]["headers"]["X-RCF-Chain-Root"] == headers["X-RCF-Marker"]


def test_subscription_filter_and_inactive(test_user, db_session, captured_posts):
    asyncio.get_event_loop().run_until_complete(
        _mk_hook(db_session, test_user["user_id"], ["deal_created"], name="only-deals"))
    asyncio.get_event_loop().run_until_complete(
        _mk_hook(db_session, test_user["user_id"], ["contact_created"], name="inactive", active=False))

    asyncio.get_event_loop().run_until_complete(
        webhook_service.trigger_webhooks(test_user["user_id"], "contact_created", {})
    )
    # only-deals is not subscribed to contact_created; inactive one is skipped.
    assert captured_posts == []


def test_create_contact_fires_contact_created(client, test_user, monkeypatch):
    """POST /api/crm/contacts must fan out a contact_created event."""
    calls: list[tuple] = []

    def fake_trigger(user_id, event_type, payload):
        calls.append((user_id, event_type, payload))

        async def _noop():
            pass

        return _noop()

    monkeypatch.setattr(webhook_service, "trigger_webhooks", fake_trigger)

    r = client.post("/api/crm/contacts",
                    headers={"Authorization": f"Bearer {test_user['token']}"},
                    json={"name": "Zapier Lead", "email": "lead@example.com"})
    assert r.status_code == 201, r.text

    assert len(calls) == 1
    user_id, event_type, payload = calls[0]
    assert user_id == test_user["user_id"]
    assert event_type == "contact_created"
    assert payload["name"] == "Zapier Lead"
    assert payload["contact_id"] == r.json()["id"]


# ── agent tools ──────────────────────────────────────────────────────────────
def test_tool_list_webhooks(client, test_user, db_session):
    h = {"Authorization": f"Bearer {test_user['token']}"}
    client.post("/api/webhooks/outgoing", headers=h,
                json={"name": "Zap", "url": "https://hooks.zapier.com/hooks/catch/9/",
                      "events": ["contact_created"]})

    ctx = ToolContext(db=db_session, user_id=test_user["user_id"], agent_id=1)
    result = asyncio.get_event_loop().run_until_complete(execute("list_webhooks", {}, ctx))
    assert result["count"] == 1
    assert result["webhooks"][0]["name"] == "Zap"
    assert result["webhooks"][0]["events"] == ["contact_created"]


def test_tool_send_webhook_unsigned(client, test_user, db_session, captured_posts):
    h = {"Authorization": f"Bearer {test_user['token']}"}
    wid = client.post("/api/webhooks/outgoing", headers=h,
                      json={"name": "Zap", "url": "https://hooks.zapier.com/hooks/catch/9/",
                            "events": []}).json()["id"]

    ctx = ToolContext(db=db_session, user_id=test_user["user_id"], agent_id=1)
    result = asyncio.get_event_loop().run_until_complete(
        execute("send_webhook", {"webhook_id": wid, "event": "agent_event",
                                 "payload": {"lead": "new"}}, ctx))
    assert result == {"ok": True, "webhook_id": wid, "name": "Zap",
                      "event": "agent_event", "signed": False}, result
    assert len(captured_posts) == 1
    assert '"lead": "new"' in captured_posts[0]["content"]


def test_tool_send_webhook_by_name_and_errors(client, test_user, db_session, captured_posts):
    h = {"Authorization": f"Bearer {test_user['token']}"}
    client.post("/api/webhooks/outgoing", headers=h,
                json={"name": "ByName", "url": "https://hooks.zapier.com/hooks/catch/10/", "events": []})
    inactive = client.post("/api/webhooks/outgoing", headers=h,
                           json={"name": "Off", "url": "https://example.com/x",
                                 "events": [], "is_active": False}).json()

    ctx = ToolContext(db=db_session, user_id=test_user["user_id"], agent_id=1)
    loop = asyncio.get_event_loop()

    by_name = loop.run_until_complete(execute("send_webhook", {"webhook_name": "ByName"}, ctx))
    assert by_name["ok"] is True and by_name["name"] == "ByName"

    missing = loop.run_until_complete(execute("send_webhook", {"webhook_id": 99999}, ctx))
    assert "error" in missing

    off = loop.run_until_complete(execute("send_webhook", {"webhook_id": inactive["id"]}, ctx))
    assert "inactive" in off["error"]

    no_args = loop.run_until_complete(execute("send_webhook", {}, ctx))
    assert "error" in no_args

    # Only the successful send reached the wire.
    assert len(captured_posts) == 1


def test_tool_send_webhook_is_scoped_to_user(client, test_user, db_session):
    """An agent must never fire another user's webhook."""
    other = client.post("/api/auth/register",
                        json={"email": "other-hook@example.com", "password": "password123", "name": "O"})
    oh = {"Authorization": f"Bearer {other.json()['access_token']}"}
    other_wid = client.post("/api/webhooks/outgoing", headers=oh,
                            json={"name": "OtherHook", "url": "https://example.com/priv",
                                  "events": []}).json()["id"]

    ctx = ToolContext(db=db_session, user_id=test_user["user_id"], agent_id=1)
    loop = asyncio.get_event_loop()
    by_id = loop.run_until_complete(execute("send_webhook", {"webhook_id": other_wid}, ctx))
    assert "error" in by_id
    by_name = loop.run_until_complete(execute("send_webhook", {"webhook_name": "OtherHook"}, ctx))
    assert "error" in by_name
    listing = loop.run_until_complete(execute("list_webhooks", {}, ctx))
    assert listing["count"] == 0


def test_default_roles_include_webhook_tools():
    """Both the default and sales tool sets expose webhook visibility."""
    from app.services.agent_runner import DEFAULT_TOOLS_BY_ROLE
    for role in ("_default", "sales"):
        assert "list_webhooks" in DEFAULT_TOOLS_BY_ROLE[role]
        assert "send_webhook" in DEFAULT_TOOLS_BY_ROLE[role]


def test_tools_registered_in_registry():
    from app.tools import REGISTRY
    assert "list_webhooks" in REGISTRY
    assert "send_webhook" in REGISTRY
