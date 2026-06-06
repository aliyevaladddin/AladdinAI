"""Test agent endpoints."""


def test_create_agent(client, auth_headers):
    """Test creating a new agent."""
    response = client.post(
        "/api/agents",
        headers=auth_headers,
        json={
            "name": "test_agent",
            "role": "assistant",
            "system_prompt": "You are a helpful assistant",
            "model": "meta/llama-3.1-8b-instruct",
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test_agent"
    assert data["role"] == "assistant"
    assert data["system_prompt"] == "You are a helpful assistant"


def test_list_agents(client, auth_headers):
    """Test listing user's agents."""
    # Create an agent first
    client.post(
        "/api/agents",
        headers=auth_headers,
        json={
            "name": "agent1",
            "role": "assistant",
            "system_prompt": "Test",
            "model": "meta/llama-3.1-8b-instruct"
        }
    )

    # List agents
    response = client.get("/api/agents", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == "agent1"


def test_get_agent_by_id(client, auth_headers):
    """Test getting agent by ID."""
    # Create agent
    create_response = client.post(
        "/api/agents",
        headers=auth_headers,
        json={
            "name": "test_agent",
            "role": "assistant",
            "system_prompt": "Test",
            "model": "meta/llama-3.1-8b-instruct"
        }
    )
    agent_id = create_response.json()["id"]

    # Get agent
    response = client.get(f"/api/agents/{agent_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == agent_id
    assert data["name"] == "test_agent"


def test_update_agent(client, auth_headers):
    """Test updating agent configuration."""
    # Create agent
    create_response = client.post(
        "/api/agents",
        headers=auth_headers,
        json={
            "name": "test_agent",
            "role": "assistant",
            "system_prompt": "Original prompt",
            "model": "meta/llama-3.1-8b-instruct"
        }
    )
    agent_id = create_response.json()["id"]

    # Update agent
    response = client.put(
        f"/api/agents/{agent_id}",
        headers=auth_headers,
        json={
            "system_prompt": "Updated prompt",
            "role": "updated_role"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["system_prompt"] == "Updated prompt"
    assert data["role"] == "updated_role"


def test_delete_agent(client, auth_headers):
    """Test deleting an agent."""
    # Create agent
    create_response = client.post(
        "/api/agents",
        headers=auth_headers,
        json={
            "name": "test_agent",
            "role": "assistant",
            "system_prompt": "Test",
            "model": "meta/llama-3.1-8b-instruct"
        }
    )
    agent_id = create_response.json()["id"]

    # Delete agent
    response = client.delete(f"/api/agents/{agent_id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify deleted
    get_response = client.get(f"/api/agents/{agent_id}", headers=auth_headers)
    assert get_response.status_code == 404


def test_create_agent_unauthorized(client):
    """Test creating agent without auth fails."""
    response = client.post(
        "/api/agents",
        json={
            "name": "test_agent",
            "role": "assistant",
            "system_prompt": "Test",
            "model": "meta/llama-3.1-8b-instruct"
        }
    )
    assert response.status_code == 401


def test_create_duplicate_agent_name(client, auth_headers):
    """Test creating agent with duplicate name fails."""
    # Create first agent
    client.post(
        "/api/agents",
        headers=auth_headers,
        json={
            "name": "test_agent",
            "role": "assistant",
            "system_prompt": "Test",
            "model": "meta/llama-3.1-8b-instruct"
        }
    )

    # Try to create duplicate
    response = client.post(
        "/api/agents",
        headers=auth_headers,
        json={
            "name": "test_agent",
            "role": "assistant",
            "system_prompt": "Test",
            "model": "meta/llama-3.1-8b-instruct"
        }
    )
    assert response.status_code == 400
