# NOTICE: This file is protected under RCF-PL
"""Tests for notifications router — CRUD + unread count."""


def test_list_notifications(client, auth_headers):
    r = client.get("/api/notifications", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_unread_count(client, auth_headers):
    r = client.get("/api/notifications/unread-count", headers=auth_headers)
    assert r.status_code == 200
    assert "count" in r.json()


def test_notifications_unauthenticated(client):
    r = client.get("/api/notifications")
    assert r.status_code == 401


def test_mark_all_read(client, auth_headers):
    r = client.post("/api/notifications/read-all", headers=auth_headers)
    assert r.status_code in (200, 204)


def test_unread_count_after_read_all(client, auth_headers):
    client.post("/api/notifications/read-all", headers=auth_headers)
    r = client.get("/api/notifications/unread-count", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["count"] == 0
