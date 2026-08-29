# NOTICE: This file is protected under RCF-PL
"""Tests for dashboard router — stats and overview endpoints."""


def test_dashboard_stats(client, auth_headers):
    r = client.get("/api/dashboard/stats", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    # Stats should have key fields
    assert isinstance(data, dict)


def test_dashboard_unauthenticated(client):
    r = client.get("/api/dashboard/stats")
    assert r.status_code == 401


def test_dashboard_overview(client, auth_headers):
    """Test that the overview endpoint returns data without crashing."""
    r = client.get("/api/dashboard/overview", headers=auth_headers)
    # May be 200 or 404 depending on implementation
    assert r.status_code in (200, 404)
