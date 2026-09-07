# NOTICE: This file is protected under RCF-PL
"""Tests for the WhatsApp Baileys bridge plumbing.

Covers the pure/lokal parts only — the Node daemon itself needs a live
WhatsApp connection and is exercised manually via the QR flow:

- X-Bridge-Secret verification of the internal webhook
- parse_whatsapp_baileys payload shape
- bridge manager: stale-socket handling without spawning a daemon
"""
import asyncio
import logging
import os
import tempfile
from types import SimpleNamespace

from starlette.requests import Request

from app.routers.webhooks import _verify_whatsapp_baileys
from app.services import whatsapp_bridge
from app.services.messaging_service import parse_whatsapp_baileys


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_request(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/webhooks/whatsapp_baileys/1",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }
    return Request(scope)


# ── X-Bridge-Secret verification ────────────────────────────────────────────

def test_verify_baileys_with_secret_accepts_correct_header():
    channel = SimpleNamespace(id=1, webhook_secret="s3cret")
    req = _make_request({"X-Bridge-Secret": "s3cret"})
    assert _verify_whatsapp_baileys(channel, req, b"{}") is True


def test_verify_baileys_with_secret_rejects_wrong_header():
    channel = SimpleNamespace(id=1, webhook_secret="s3cret")
    assert _verify_whatsapp_baileys(channel, _make_request({"X-Bridge-Secret": "wrong"}), b"{}") is False


def test_verify_baileys_with_secret_rejects_missing_header():
    channel = SimpleNamespace(id=1, webhook_secret="s3cret")
    assert _verify_whatsapp_baileys(channel, _make_request({}), b"{}") is False


def test_verify_baileys_without_secret_fails_closed(caplog):
    """A channel without a webhook_secret must reject every request (fail closed).

    Accepting unsigned posts would reopen the message-injection hole this
    branch exists to close; backfill happens on the first QR open instead.
    """
    channel = SimpleNamespace(id=2, webhook_secret=None)
    with caplog.at_level(logging.ERROR):
        assert _verify_whatsapp_baileys(channel, _make_request({}), b"{}") is False
    assert "no webhook_secret" in caplog.text


# ── payload parsing ──────────────────────────────────────────────────────────

def test_parse_whatsapp_baileys_payload():
    payload = {"sender_id": "49123@s.whatsapp.net", "sender_name": "John", "text": "hello"}
    sender_id, sender_name, text = parse_whatsapp_baileys(payload)
    assert sender_id == "49123@s.whatsapp.net"
    assert sender_name == "John"
    assert text == "hello"


def test_parse_whatsapp_baileys_empty_payload():
    assert parse_whatsapp_baileys({}) == ("", "", "")


# ── bridge manager: no-daemon paths (must NOT spawn node) ───────────────────

def test_ping_false_without_socket_file():
    # A channel id that has no daemon running — no /tmp socket file exists.
    assert asyncio.run(whatsapp_bridge.ping(999999)) is False


def test_ping_false_and_cleanup_on_stale_socket():
    with tempfile.TemporaryDirectory() as tmp:
        sock = os.path.join(tmp, "stale.sock")
        open(sock, "w").close()  # socket file without a listener

        # Point the manager at our temp dir via the real socket_path logic.
        orig = whatsapp_bridge.socket_path
        whatsapp_bridge.socket_path = lambda cid: sock
        try:
            assert asyncio.run(whatsapp_bridge.ping(1)) is False
            assert not os.path.exists(sock)  # stale file removed
        finally:
            whatsapp_bridge.socket_path = orig


def test_send_command_error_when_bridge_dead(monkeypatch):
    async def fake_ping(cid, timeout=2.0):
        return False

    async def fake_ensure(channel, timeout=10.0):
        return False

    monkeypatch.setattr(whatsapp_bridge, "ping", fake_ping)
    monkeypatch.setattr(whatsapp_bridge, "ensure_bridge", fake_ensure)

    channel = SimpleNamespace(id=999999, webhook_secret="x")
    res = asyncio.run(
        whatsapp_bridge.send_command({"type": "get-qr"}, channel, timeout=2.0)
    )
    assert res["type"] == "error"


def test_socket_path_is_per_channel():
    assert whatsapp_bridge.socket_path(5) != whatsapp_bridge.socket_path(6)
    assert whatsapp_bridge.socket_path(5).endswith("aladdin_whatsapp_5.sock")
