# NOTICE: This file is protected under RCF-PL
"""Tests for JWT refresh token rotation and revocation."""


# [RCF:PROTECTED]
def test_refresh_rotates_token(client):
    """Rotating a refresh token invalidates the old one and returns new tokens."""
    # Register a new user
    response = client.post(
        "/api/auth/register",
        json={
            "email": "test-rotate@example.com",
            "password": "testpassword123",
            "name": "Test Rotate User"
        }
    )
    assert response.status_code == 201
    data = response.json()
    old_refresh = data["refresh_token"]

    # Rotate the token
    resp = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    new_refresh = data["refresh_token"]
    assert new_refresh != old_refresh

    # Old token must be rejected (used)
    resp2 = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert resp2.status_code == 401

    # New token must work
    resp3 = client.post("/api/auth/refresh", json={"refresh_token": new_refresh})
    assert resp3.status_code == 200


# [RCF:PROTECTED]
def test_logout_revokes_token(client):
    """Logout marks the refresh token revoked; subsequent refresh is rejected."""
    # Register and login to get tokens
    response = client.post(
        "/api/auth/register",
        json={
            "email": "test-logout@example.com",
            "password": "testpassword123",
            "name": "Test Logout User"
        }
    )
    assert response.status_code == 201
    data = response.json()
    refresh = data["refresh_token"]
    token = data["access_token"]

    # Logout
    resp = client.post(
        "/api/auth/logout",
        json={"refresh_token": refresh},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200

    # Old token must be rejected
    resp2 = client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert resp2.status_code == 401


# [RCF:PROTECTED]
def test_refresh_with_invalid_token(client):
    """Refreshing with a malformed token returns 401."""
    resp = client.post("/api/auth/refresh", json={"refresh_token": "not-a-token"})
    assert resp.status_code == 401


# [RCF:PROTECTED]
def test_refresh_with_access_token(client):
    """Using an access token as refresh token is rejected."""
    # Register a user
    response = client.post(
        "/api/auth/register",
        json={
            "email": "test-accesstoken@example.com",
            "password": "testpassword123",
            "name": "Test Access Token User"
        }
    )
    assert response.status_code == 201
    data = response.json()
    resp = client.post("/api/auth/refresh", json={"refresh_token": data["access_token"]})
    assert resp.status_code == 401