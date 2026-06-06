"""Test provider management endpoints."""
import pytest


def test_list_providers_empty(client, auth_headers):
    """Test listing providers when none exist."""
    response = client.get("/api/providers", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_create_provider(client, auth_headers):
    """Test creating a new LLM provider."""
    response = client.post(
        "/api/providers",
        headers=auth_headers,
        json={
            "name": "My NVIDIA NIM",
            "type": "nim",
            "api_key": "nvapi-test-key",
            "base_url": "https://integrate.api.nvidia.com/v1"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My NVIDIA NIM"
    assert data["type"] == "nim"
    assert data["base_url"] == "https://integrate.api.nvidia.com/v1"
    # API key should be encrypted, not returned in plain
    assert "api_key" not in data


def test_create_provider_without_key(client, auth_headers):
    """Test creating provider without API key (e.g., Ollama local)."""
    response = client.post(
        "/api/providers",
        headers=auth_headers,
        json={
            "name": "Local Ollama",
            "type": "ollama",
            "base_url": "http://localhost:11434"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Local Ollama"
    assert data["type"] == "ollama"


def test_list_providers(client, auth_headers):
    """Test listing user's providers."""
    # Create two providers
    client.post(
        "/api/providers",
        headers=auth_headers,
        json={
            "name": "Provider 1",
            "type": "openai",
            "api_key": "sk-test1",
            "base_url": "https://api.openai.com/v1"
        }
    )
    client.post(
        "/api/providers",
        headers=auth_headers,
        json={
            "name": "Provider 2",
            "type": "nim",
            "api_key": "nvapi-test2",
            "base_url": "https://integrate.api.nvidia.com/v1"
        }
    )

    response = client.get("/api/providers", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    names = {p["name"] for p in data}
    assert "Provider 1" in names
    assert "Provider 2" in names


def test_update_provider(client, auth_headers):
    """Test updating provider configuration."""
    create_response = client.post(
        "/api/providers",
        headers=auth_headers,
        json={
            "name": "Original Provider",
            "type": "openai",
            "api_key": "sk-original",
            "base_url": "https://api.openai.com/v1"
        }
    )
    provider_id = create_response.json()["id"]

    response = client.put(
        f"/api/providers/{provider_id}",
        headers=auth_headers,
        json={
            "name": "Updated Provider",
            "type": "openai",
            "api_key": "sk-updated",
            "base_url": "https://api.openai.com/v1"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Provider"


def test_delete_provider(client, auth_headers):
    """Test deleting a provider."""
    create_response = client.post(
        "/api/providers",
        headers=auth_headers,
        json={
            "name": "To Delete",
            "type": "nim",
            "api_key": "nvapi-test",
            "base_url": "https://integrate.api.nvidia.com/v1"
        }
    )
    provider_id = create_response.json()["id"]

    response = client.delete(f"/api/providers/{provider_id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify it's gone from list
    list_response = client.get("/api/providers", headers=auth_headers)
    provider_ids = [p["id"] for p in list_response.json()]
    assert provider_id not in provider_ids


def test_get_provider_models_not_connected(client, auth_headers):
    """Test getting models from a provider that hasn't been connected."""
    create_response = client.post(
        "/api/providers",
        headers=auth_headers,
        json={
            "name": "Not Connected",
            "type": "nim",
            "api_key": "nvapi-test",
            "base_url": "https://integrate.api.nvidia.com/v1"
        }
    )
    provider_id = create_response.json()["id"]

    response = client.get(f"/api/providers/{provider_id}/models", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["models"] == []
    assert "hint" in data


def test_disconnect_provider(client, auth_headers):
    """Test disconnecting a provider."""
    create_response = client.post(
        "/api/providers",
        headers=auth_headers,
        json={
            "name": "Test Provider",
            "type": "nim",
            "api_key": "nvapi-test",
            "base_url": "https://integrate.api.nvidia.com/v1"
        }
    )
    provider_id = create_response.json()["id"]

    response = client.post(f"/api/providers/{provider_id}/disconnect", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "disconnected"


def test_provider_user_scoping(client, test_user):
    """Test users cannot access other users' providers."""
    # Create second user
    user2_response = client.post(
        "/api/auth/register",
        json={
            "email": "provider_user2@example.com",
            "password": "password123",
            "name": "Provider User2"
        }
    )
    user2_token = user2_response.json()["access_token"]
    user2_headers = {"Authorization": f"Bearer {user2_token}"}

    # User1 creates provider
    user1_headers = {"Authorization": f"Bearer {test_user['token']}"}
    create_response = client.post(
        "/api/providers",
        headers=user1_headers,
        json={
            "name": "User1 Provider",
            "type": "nim",
            "api_key": "nvapi-user1",
            "base_url": "https://integrate.api.nvidia.com/v1"
        }
    )
    provider_id = create_response.json()["id"]

    # User2 tries to access user1's provider
    response = client.get(f"/api/providers/{provider_id}/models", headers=user2_headers)
    assert response.status_code == 404


def test_provider_unauthorized(client):
    """Test accessing providers without auth fails."""
    response = client.get("/api/providers")
    assert response.status_code == 401


def test_update_nonexistent_provider(client, auth_headers):
    """Test updating a provider that doesn't exist."""
    response = client.put(
        "/api/providers/99999",
        headers=auth_headers,
        json={
            "name": "Nonexistent",
            "type": "nim",
            "api_key": "test",
            "base_url": "https://example.com"
        }
    )
    assert response.status_code == 404


def test_delete_nonexistent_provider(client, auth_headers):
    """Test deleting a provider that doesn't exist."""
    response = client.delete("/api/providers/99999", headers=auth_headers)
    assert response.status_code == 404
