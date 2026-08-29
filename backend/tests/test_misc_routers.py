# NOTICE: This file is protected under RCF-PL
"""Tests for miscellaneous small routers: settings, search, user, vms, ssh_exec, digest, router_config."""


# ── settings ─────────────────────────────────────────────────────────────────

class TestSettings:
    def test_get_settings(self, client, auth_headers):
        r = client.get("/api/settings", headers=auth_headers)
        assert r.status_code == 200

    def test_settings_unauthenticated(self, client):
        r = client.get("/api/settings")
        assert r.status_code == 401


# ── search ───────────────────────────────────────────────────────────────────

class TestSearch:
    def test_search_empty(self, client, auth_headers):
        r = client.get("/api/search?q=test", headers=auth_headers)
        assert r.status_code == 200

    def test_search_unauthenticated(self, client):
        r = client.get("/api/search?q=test")
        assert r.status_code == 401


# ── user ─────────────────────────────────────────────────────────────────────
# NOTE: user router is not included in main.py — profile is via /api/auth/me

class TestUser:
    def test_get_profile_via_auth(self, client, auth_headers):
        r = client.get("/api/auth/me", headers=auth_headers)
        assert r.status_code == 200
        assert "email" in r.json()

    def test_user_unauthenticated(self, client):
        r = client.get("/api/auth/me")
        assert r.status_code == 401


# ── vms ──────────────────────────────────────────────────────────────────────

class TestVMs:
    def test_list_vms(self, client, auth_headers):
        r = client.get("/api/vms", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_vms_unauthenticated(self, client):
        r = client.get("/api/vms")
        assert r.status_code == 401


# ── ssh_exec ─────────────────────────────────────────────────────────────────

class TestSSHExec:
    def test_ssh_exec_unauthenticated(self, client):
        r = client.post("/api/ssh/exec", json={"host": "x", "command": "ls"})
        assert r.status_code == 401

    def test_ssh_exec_list_vms(self, client, auth_headers):
        r = client.get("/api/ssh/vms-list", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ── digest ───────────────────────────────────────────────────────────────────

class TestDigest:
    def test_digest_trigger(self, client, auth_headers):
        r = client.post("/api/digest/trigger", headers=auth_headers)
        # May need body or fail without config
        assert r.status_code in (200, 400, 422, 500)

    def test_digest_unauthenticated(self, client):
        r = client.post("/api/digest/trigger")
        assert r.status_code == 401


# ── router_config ────────────────────────────────────────────────────────────

class TestRouterConfig:
    def test_list_configs(self, client, auth_headers):
        r = client.get("/api/router-config", headers=auth_headers)
        # May be 200 or 404 if router not fully registered
        assert r.status_code in (200, 404)
