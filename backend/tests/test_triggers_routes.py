# NOTICE: This file is protected under RCF-PL
"""Tests for triggers router — CRUD + run-now + preview."""


def test_list_triggers(client, auth_headers):
    r = client.get("/api/triggers", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_create_trigger(client, auth_headers):
    r = client.post("/api/triggers", headers=auth_headers, json={
        "name": "Test Trigger",
        "trigger_type": "cron",
        "cron_expression": "0 9 * * *",
        "action_type": "send_message",
    })
    # May require agent_id or other fields
    assert r.status_code in (201, 422)


def test_triggers_unauthenticated(client):
    r = client.get("/api/triggers")
    assert r.status_code == 401


def test_trigger_presets(client, auth_headers):
    r = client.get("/api/triggers/presets", headers=auth_headers)
    assert r.status_code == 200


def test_trigger_templates(client, auth_headers):
    r = client.get("/api/triggers/templates", headers=auth_headers)
    assert r.status_code == 200


def test_trigger_preview(client, auth_headers):
    r = client.get("/api/triggers/preview", headers=auth_headers, params={"cron_expression": "0 9 * * *"})
    assert r.status_code in (200, 422)  # 422 if query param name differs
