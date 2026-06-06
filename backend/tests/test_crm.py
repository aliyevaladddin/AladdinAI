"""Test CRM endpoints: Contacts, Deals, Activities."""
import pytest


# ──────────────────────────────────────────────────────────────────────────────
# CONTACTS
# ──────────────────────────────────────────────────────────────────────────────

def test_create_contact(client, auth_headers):
    """Test creating a new contact."""
    response = client.post(
        "/api/crm/contacts",
        headers=auth_headers,
        json={
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "+1234567890",
            "company": "Acme Corp",
            "tags": ["vip", "enterprise"],
            "source": "referral",
            "notes": "Met at conference"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "John Doe"
    assert data["email"] == "john@example.com"
    assert data["company"] == "Acme Corp"
    assert "vip" in data["tags"]


def test_list_contacts(client, auth_headers):
    """Test listing user's contacts."""
    # Create two contacts
    client.post(
        "/api/crm/contacts",
        headers=auth_headers,
        json={"name": "Alice Smith", "email": "alice@example.com"}
    )
    client.post(
        "/api/crm/contacts",
        headers=auth_headers,
        json={"name": "Bob Johnson", "company": "TechCorp"}
    )

    response = client.get("/api/crm/contacts", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    names = {c["name"] for c in data}
    assert "Alice Smith" in names
    assert "Bob Johnson" in names


def test_search_contacts(client, auth_headers):
    """Test searching contacts by name, email, or company."""
    client.post(
        "/api/crm/contacts",
        headers=auth_headers,
        json={"name": "Jane Doe", "email": "jane@techstart.com", "company": "TechStart"}
    )
    client.post(
        "/api/crm/contacts",
        headers=auth_headers,
        json={"name": "Mike Wilson", "email": "mike@other.com"}
    )

    # Search by company
    response = client.get("/api/crm/contacts?search=TechStart", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Jane Doe"


def test_get_contact_by_id(client, auth_headers):
    """Test getting contact by ID."""
    create_response = client.post(
        "/api/crm/contacts",
        headers=auth_headers,
        json={"name": "Test Contact", "email": "test@example.com"}
    )
    contact_id = create_response.json()["id"]

    response = client.get(f"/api/crm/contacts/{contact_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == contact_id
    assert data["name"] == "Test Contact"


def test_update_contact(client, auth_headers):
    """Test updating contact information."""
    create_response = client.post(
        "/api/crm/contacts",
        headers=auth_headers,
        json={"name": "Original Name", "email": "original@example.com"}
    )
    contact_id = create_response.json()["id"]

    response = client.put(
        f"/api/crm/contacts/{contact_id}",
        headers=auth_headers,
        json={"name": "Updated Name", "company": "New Company"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["company"] == "New Company"
    assert data["email"] == "original@example.com"  # unchanged


def test_delete_contact(client, auth_headers):
    """Test deleting a contact."""
    create_response = client.post(
        "/api/crm/contacts",
        headers=auth_headers,
        json={"name": "To Delete", "email": "delete@example.com"}
    )
    contact_id = create_response.json()["id"]

    response = client.delete(f"/api/crm/contacts/{contact_id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify deleted
    get_response = client.get(f"/api/crm/contacts/{contact_id}", headers=auth_headers)
    assert get_response.status_code == 404


def test_contact_unauthorized(client):
    """Test accessing contacts without auth fails."""
    response = client.get("/api/crm/contacts")
    assert response.status_code == 401


def test_contact_user_scoping(client, test_user):
    """Test users cannot see other users' contacts."""
    # Create second user
    user2_response = client.post(
        "/api/auth/register",
        json={
            "email": "user2@example.com",
            "password": "password123",
            "name": "User2"
        }
    )
    user2_token = user2_response.json()["access_token"]
    user2_headers = {"Authorization": f"Bearer {user2_token}"}

    # User1 creates contact
    user1_headers = {"Authorization": f"Bearer {test_user['token']}"}
    create_response = client.post(
        "/api/crm/contacts",
        headers=user1_headers,
        json={"name": "User1 Contact", "email": "user1contact@example.com"}
    )
    contact_id = create_response.json()["id"]

    # User2 tries to access user1's contact
    response = client.get(f"/api/crm/contacts/{contact_id}", headers=user2_headers)
    assert response.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# DEALS
# ──────────────────────────────────────────────────────────────────────────────

def test_create_deal(client, auth_headers):
    """Test creating a new deal."""
    # Create contact first
    contact_response = client.post(
        "/api/crm/contacts",
        headers=auth_headers,
        json={"name": "Deal Contact", "email": "deal@example.com"}
    )
    contact_id = contact_response.json()["id"]

    response = client.post(
        "/api/crm/deals",
        headers=auth_headers,
        json={
            "contact_id": contact_id,
            "title": "Enterprise Deal",
            "stage": "lead",
            "amount": 50000.0,
            "currency": "USD",
            "probability": 25,
            "notes": "Hot lead from conference"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Enterprise Deal"
    assert data["stage"] == "lead"
    assert data["amount"] == 50000.0
    assert data["contact_id"] == contact_id


def test_list_deals(client, auth_headers):
    """Test listing user's deals."""
    contact_response = client.post(
        "/api/crm/contacts",
        headers=auth_headers,
        json={"name": "Contact", "email": "contact@example.com"}
    )
    contact_id = contact_response.json()["id"]

    # Create two deals
    client.post(
        "/api/crm/deals",
        headers=auth_headers,
        json={"contact_id": contact_id, "title": "Deal 1", "stage": "lead"}
    )
    client.post(
        "/api/crm/deals",
        headers=auth_headers,
        json={"contact_id": contact_id, "title": "Deal 2", "stage": "won"}
    )

    response = client.get("/api/crm/deals", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_filter_deals_by_stage(client, auth_headers):
    """Test filtering deals by stage."""
    contact_response = client.post(
        "/api/crm/contacts",
        headers=auth_headers,
        json={"name": "Contact", "email": "contact@example.com"}
    )
    contact_id = contact_response.json()["id"]

    client.post(
        "/api/crm/deals",
        headers=auth_headers,
        json={"contact_id": contact_id, "title": "Won Deal", "stage": "won"}
    )
    client.post(
        "/api/crm/deals",
        headers=auth_headers,
        json={"contact_id": contact_id, "title": "Lost Deal", "stage": "lost"}
    )

    # Filter by won stage
    response = client.get("/api/crm/deals?stage=won", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Won Deal"


def test_update_deal(client, auth_headers):
    """Test updating deal information."""
    contact_response = client.post(
        "/api/crm/contacts",
        headers=auth_headers,
        json={"name": "Contact", "email": "contact@example.com"}
    )
    contact_id = contact_response.json()["id"]

    create_response = client.post(
        "/api/crm/deals",
        headers=auth_headers,
        json={"contact_id": contact_id, "title": "Original Title", "amount": 1000.0}
    )
    deal_id = create_response.json()["id"]

    response = client.put(
        f"/api/crm/deals/{deal_id}",
        headers=auth_headers,
        json={"title": "Updated Title", "amount": 2000.0}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["amount"] == 2000.0


def test_move_deal_stage(client, auth_headers):
    """Test moving deal to different stage."""
    contact_response = client.post(
        "/api/crm/contacts",
        headers=auth_headers,
        json={"name": "Contact", "email": "contact@example.com"}
    )
    contact_id = contact_response.json()["id"]

    create_response = client.post(
        "/api/crm/deals",
        headers=auth_headers,
        json={"contact_id": contact_id, "title": "Deal", "stage": "lead"}
    )
    deal_id = create_response.json()["id"]

    response = client.put(
        f"/api/crm/deals/{deal_id}/stage?stage=proposal",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["stage"] == "proposal"


def test_move_deal_invalid_stage(client, auth_headers):
    """Test moving deal to invalid stage fails."""
    contact_response = client.post(
        "/api/crm/contacts",
        headers=auth_headers,
        json={"name": "Contact", "email": "contact@example.com"}
    )
    contact_id = contact_response.json()["id"]

    create_response = client.post(
        "/api/crm/deals",
        headers=auth_headers,
        json={"contact_id": contact_id, "title": "Deal", "stage": "lead"}
    )
    deal_id = create_response.json()["id"]

    response = client.put(
        f"/api/crm/deals/{deal_id}/stage?stage=invalid_stage",
        headers=auth_headers
    )
    assert response.status_code == 400


def test_delete_deal(client, auth_headers):
    """Test deleting a deal."""
    contact_response = client.post(
        "/api/crm/contacts",
        headers=auth_headers,
        json={"name": "Contact", "email": "contact@example.com"}
    )
    contact_id = contact_response.json()["id"]

    create_response = client.post(
        "/api/crm/deals",
        headers=auth_headers,
        json={"contact_id": contact_id, "title": "To Delete"}
    )
    deal_id = create_response.json()["id"]

    response = client.delete(f"/api/crm/deals/{deal_id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify deleted
    get_response = client.get(f"/api/crm/deals/{deal_id}", headers=auth_headers)
    assert get_response.status_code == 404


def test_deal_user_scoping(client, test_user):
    """Test users cannot see other users' deals."""
    # Create second user
    user2_response = client.post(
        "/api/auth/register",
        json={
            "email": "dealuser2@example.com",
            "password": "password123",
            "name": "Deal User2"
        }
    )
    user2_token = user2_response.json()["access_token"]
    user2_headers = {"Authorization": f"Bearer {user2_token}"}

    # User1 creates deal
    user1_headers = {"Authorization": f"Bearer {test_user['token']}"}
    contact_response = client.post(
        "/api/crm/contacts",
        headers=user1_headers,
        json={"name": "Contact", "email": "contact@example.com"}
    )
    contact_id = contact_response.json()["id"]

    create_response = client.post(
        "/api/crm/deals",
        headers=user1_headers,
        json={"contact_id": contact_id, "title": "Private Deal"}
    )
    deal_id = create_response.json()["id"]

    # User2 tries to access user1's deal
    response = client.get(f"/api/crm/deals/{deal_id}", headers=user2_headers)
    assert response.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# ACTIVITIES
# ──────────────────────────────────────────────────────────────────────────────

def test_create_activity(client, auth_headers):
    """Test creating a new activity."""
    contact_response = client.post(
        "/api/crm/contacts",
        headers=auth_headers,
        json={"name": "Activity Contact", "email": "activity@example.com"}
    )
    contact_id = contact_response.json()["id"]

    response = client.post(
        "/api/crm/activities",
        headers=auth_headers,
        json={
            "contact_id": contact_id,
            "type": "email_in",
            "channel": "gmail",
            "subject": "Meeting request",
            "content": "Can we schedule a call?",
            "metadata_json": {"priority": "high"}
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "email_in"
    assert data["subject"] == "Meeting request"
    assert data["contact_id"] == contact_id


def test_list_activities(client, auth_headers):
    """Test listing activities."""
    contact_response = client.post(
        "/api/crm/contacts",
        headers=auth_headers,
        json={"name": "Contact", "email": "contact@example.com"}
    )
    contact_id = contact_response.json()["id"]

    # Create activities
    client.post(
        "/api/crm/activities",
        headers=auth_headers,
        json={"contact_id": contact_id, "type": "email_in", "subject": "Activity 1"}
    )
    client.post(
        "/api/crm/activities",
        headers=auth_headers,
        json={"contact_id": contact_id, "type": "note", "content": "Activity 2"}
    )

    response = client.get("/api/crm/activities", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_filter_activities_by_type(client, auth_headers):
    """Test filtering activities by type."""
    contact_response = client.post(
        "/api/crm/contacts",
        headers=auth_headers,
        json={"name": "Contact", "email": "contact@example.com"}
    )
    contact_id = contact_response.json()["id"]

    client.post(
        "/api/crm/activities",
        headers=auth_headers,
        json={"contact_id": contact_id, "type": "email_in", "subject": "Email"}
    )
    client.post(
        "/api/crm/activities",
        headers=auth_headers,
        json={"contact_id": contact_id, "type": "call", "content": "Phone call"}
    )

    response = client.get("/api/crm/activities?type=call", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["type"] == "call"


def test_filter_activities_by_channel(client, auth_headers):
    """Test filtering activities by channel."""
    contact_response = client.post(
        "/api/crm/contacts",
        headers=auth_headers,
        json={"name": "Contact", "email": "contact@example.com"}
    )
    contact_id = contact_response.json()["id"]

    client.post(
        "/api/crm/activities",
        headers=auth_headers,
        json={"contact_id": contact_id, "type": "message_in", "channel": "telegram"}
    )
    client.post(
        "/api/crm/activities",
        headers=auth_headers,
        json={"contact_id": contact_id, "type": "message_in", "channel": "whatsapp"}
    )

    response = client.get("/api/crm/activities?channel=telegram", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["channel"] == "telegram"


def test_update_activity(client, auth_headers):
    """Test updating activity contact association."""
    contact1 = client.post(
        "/api/crm/contacts",
        headers=auth_headers,
        json={"name": "Contact 1", "email": "contact1@example.com"}
    ).json()
    contact2 = client.post(
        "/api/crm/contacts",
        headers=auth_headers,
        json={"name": "Contact 2", "email": "contact2@example.com"}
    ).json()

    create_response = client.post(
        "/api/crm/activities",
        headers=auth_headers,
        json={"contact_id": contact1["id"], "type": "note", "content": "Test note"}
    )
    activity_id = create_response.json()["id"]

    # Reassign to contact2
    response = client.patch(
        f"/api/crm/activities/{activity_id}",
        headers=auth_headers,
        json={"contact_id": contact2["id"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["contact_id"] == contact2["id"]


def test_get_contact_activities(client, auth_headers):
    """Test getting activities for a specific contact."""
    contact_response = client.post(
        "/api/crm/contacts",
        headers=auth_headers,
        json={"name": "Contact", "email": "contact@example.com"}
    )
    contact_id = contact_response.json()["id"]

    # Create activities for this contact
    client.post(
        "/api/crm/activities",
        headers=auth_headers,
        json={"contact_id": contact_id, "type": "email_in", "subject": "Email 1"}
    )
    client.post(
        "/api/crm/activities",
        headers=auth_headers,
        json={"contact_id": contact_id, "type": "note", "content": "Note 1"}
    )

    response = client.get(f"/api/crm/contacts/{contact_id}/activities", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_get_contact_deals(client, auth_headers):
    """Test getting deals for a specific contact."""
    contact_response = client.post(
        "/api/crm/contacts",
        headers=auth_headers,
        json={"name": "Contact", "email": "contact@example.com"}
    )
    contact_id = contact_response.json()["id"]

    # Create deals for this contact
    client.post(
        "/api/crm/deals",
        headers=auth_headers,
        json={"contact_id": contact_id, "title": "Deal 1", "stage": "lead"}
    )
    client.post(
        "/api/crm/deals",
        headers=auth_headers,
        json={"contact_id": contact_id, "title": "Deal 2", "stage": "won"}
    )

    response = client.get(f"/api/crm/contacts/{contact_id}/deals", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
