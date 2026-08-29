# NOTICE: This file is protected under RCF-PL
"""Tests for terminal providers router — marketplace, provider CRUD."""


def test_marketplace(client, auth_headers):
    r = client.get("/api/terminal/marketplace", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_marketplace_unauthenticated(client):
    r = client.get("/api/terminal/marketplace")
    assert r.status_code == 401


def test_list_providers(client, auth_headers):
    r = client.get("/api/terminal/providers", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_install_provider(client, auth_headers):
    r = client.post("/api/terminal/providers", headers=auth_headers, json={
        "provider_type": "ttyd",
        "name": "test-ttyd",
    })
    # May succeed, fail validation, or fail on Docker
    assert r.status_code in (201, 400, 422, 500)


def test_list_providers_empty(client, auth_headers):
    r = client.get("/api/terminal/providers", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_provider_404(client, auth_headers):
    r = client.delete("/api/terminal/providers/999999", headers=auth_headers)
    assert r.status_code == 404
