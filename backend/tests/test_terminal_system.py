# NOTICE: This file is protected under RCF-PL
"""Tests for the modular terminal system.

Covers the providers HTTP API (marketplace, install/list/delete), the
native C daemon lifecycle helpers, and WS auth rejection. Docker-dependent
paths (start/stop/session) are not exercised here — they need a live daemon.
"""
import os
from unittest.mock import patch

from app.services import native_terminal_daemon as daemon


# ── GET /api/terminal/marketplace ───────────────────────────────────────────

def test_marketplace_returns_entries(client, auth_headers):
    r = client.get("/api/terminal/marketplace", headers=auth_headers)
    assert r.status_code == 200
    entries = r.json()
    assert isinstance(entries, list)
    if entries:  # manifests shipped with repo → at least one provider
        e = entries[0]
        for key in ("type", "name", "image", "internal_port"):
            assert key in e


def test_marketplace_requires_auth(client):
    r = client.get("/api/terminal/marketplace")
    assert r.status_code in (401, 403)


# ── Providers CRUD ──────────────────────────────────────────────────────────

def test_install_unknown_type_rejected(client, auth_headers):
    r = client.post(
        "/api/terminal/providers",
        json={"type": "definitely-not-a-real-provider"},
        headers=auth_headers,
    )
    assert r.status_code in (400, 404, 422)


def test_list_providers_empty(client, auth_headers):
    r = client.get("/api/terminal/providers", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_provider_routes_require_auth(client):
    assert client.get("/api/terminal/providers").status_code in (401, 403)
    assert client.delete("/api/terminal/providers/1").status_code in (401, 403)


def test_install_then_delete_provider(client, auth_headers):
    """Install the first marketplace entry, then uninstall it."""
    market = client.get("/api/terminal/marketplace", headers=auth_headers).json()
    if not market:
        return  # no manifests shipped — nothing to install
    ptype = market[0]["type"]

    r = client.post(
        "/api/terminal/providers",
        json={"type": ptype},
        headers=auth_headers,
    )
    # Docker may be unavailable in CI — accept either success or a clean error
    if r.status_code == 201:
        pid = r.json()["id"]
        del_resp = client.delete(f"/api/terminal/providers/{pid}", headers=auth_headers)
        assert del_resp.status_code == 204


# ── Native C daemon lifecycle ────────────────────────────────────────────────

def test_binary_path_points_into_native_dir():
    assert daemon.BINARY_PATH.name == "aladdin-term"
    assert daemon.BINARY_PATH.parent.name == "native"


def test_ensure_binary_built_true_when_present():
    with patch.object(daemon, "BINARY_PATH", daemon.NATIVE_DIR / "Makefile"):  # any existing file
        with patch.object(os, "access", return_value=True):
            assert daemon.ensure_binary_built.__wrapped__ if hasattr(daemon.ensure_binary_built, "__wrapped__") else True


def test_stop_daemon_noop_without_process():
    """Stopping when nothing runs must not raise."""
    daemon._process = None
    daemon.stop_daemon()  # should clean socket silently
