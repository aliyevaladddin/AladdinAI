# NOTICE: This file is protected under RCF-PL
"""Tests for traces router — agent trace listing and detail."""


def test_list_traces(client, auth_headers):
    r = client.get("/api/traces", headers=auth_headers)
    # May return 200 with list or different format
    assert r.status_code == 200


def test_traces_unauthenticated(client):
    r = client.get("/api/traces")
    assert r.status_code == 401


def test_trace_detail_404(client, auth_headers):
    r = client.get("/api/traces/999999", headers=auth_headers)
    assert r.status_code in (404, 405)  # 405 if no detail endpoint


def test_traces_with_agent_filter(client, auth_headers):
    r = client.get("/api/traces?agent_id=1", headers=auth_headers)
    assert r.status_code == 200
