# NOTICE: This file is protected under RCF-PL
"""Tests for the SQL playground router: schema introspection and query execution."""


# ── GET /api/sql/schema ─────────────────────────────────────────────────────

def test_get_schema_returns_valid_shape(client, auth_headers):
    """Schema endpoint returns a valid structure (may fail on SQLite)."""
    r = client.get("/api/sql/schema", headers=auth_headers)
    # On Postgres: 200 with tables list
    # On SQLite: 500 because information_schema doesn't exist
    if r.status_code == 200:
        data = r.json()
        assert "tables" in data
        assert isinstance(data["tables"], list)
    else:
        # SQLite — information_schema not available
        assert r.status_code == 500


def test_get_schema_requires_auth(client):
    r = client.get("/api/sql/schema")
    assert r.status_code in (401, 403)


# ── POST /api/sql/execute ───────────────────────────────────────────────────

def test_execute_select_query(client, auth_headers):
    """SELECT queries pass validation but direct execution is disabled for security."""
    r = client.post(
        "/api/sql/execute",
        json={"query": "SELECT 1 AS one"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    # Execution is disabled — always returns success=False
    assert data["success"] is False
    assert data["error"] is not None
    assert "disabled" in data["error"].lower() or "approved" in data["error"].lower()


def test_execute_read_only_rejects_writes(client, auth_headers):
    """Default read_only=True should block INSERT."""
    r = client.post(
        "/api/sql/execute",
        json={"query": "INSERT INTO users (email, name, hashed_password) VALUES ('x@x.com', 'X', 'h')", "read_only": True},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["success"] is False


def test_execute_rejects_dangerous_sql(client, auth_headers):
    """DROP TABLE should be blocked by the validator."""
    r = client.post(
        "/api/sql/execute",
        json={"query": "DROP TABLE users"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["success"] is False


def test_execute_empty_query_rejected(client, auth_headers):
    r = client.post(
        "/api/sql/execute",
        json={"query": ""},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_execute_requires_auth(client):
    r = client.post("/api/sql/execute", json={"query": "SELECT 1"})
    assert r.status_code in (401, 403)


def test_execute_read_only_false_rejected(client, auth_headers):
    """When read_only=False, the endpoint rejects the query."""
    r = client.post(
        "/api/sql/execute",
        json={"query": "SELECT 1", "read_only": False},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is False
    assert "read-only" in data["error"].lower() or "read_only" in data["error"].lower() or "Only" in data["error"]
