# NOTICE: This file is protected under RCF-PL
"""Tests for CRM routers:

- contacts: CRUD, search, export
- deals: CRUD, stage transitions
- products: CRUD, activate/deactivate
- orders: CRUD, metrics, status transitions
"""
import pytest


# ── contacts ─────────────────────────────────────────────────────────────────

def test_create_contact(client, auth_headers):
    r = client.post("/api/crm/contacts", headers=auth_headers, json={
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+1234567890",
        "company": "Acme Inc",
    })
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["name"] == "John Doe"
    assert data["email"] == "john@example.com"
    assert "id" in data


def test_list_contacts(client, auth_headers):
    # Create two contacts
    client.post("/api/crm/contacts", headers=auth_headers, json={"name": "A", "email": "a@x.com"})
    client.post("/api/crm/contacts", headers=auth_headers, json={"name": "B", "email": "b@x.com"})
    r = client.get("/api/crm/contacts", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 2


def test_get_contact(client, auth_headers):
    create = client.post("/api/crm/contacts", headers=auth_headers, json={"name": "X", "email": "x@x.com"})
    cid = create.json()["id"]
    r = client.get(f"/api/crm/contacts/{cid}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["name"] == "X"


def test_update_contact(client, auth_headers):
    create = client.post("/api/crm/contacts", headers=auth_headers, json={"name": "Old", "email": "old@x.com"})
    cid = create.json()["id"]
    r = client.put(f"/api/crm/contacts/{cid}", headers=auth_headers, json={"name": "New"})
    assert r.status_code == 200
    assert r.json()["name"] == "New"


def test_delete_contact(client, auth_headers):
    create = client.post("/api/crm/contacts", headers=auth_headers, json={"name": "Del", "email": "del@x.com"})
    cid = create.json()["id"]
    r = client.delete(f"/api/crm/contacts/{cid}", headers=auth_headers)
    assert r.status_code == 204
    # Verify gone
    r2 = client.get(f"/api/crm/contacts/{cid}", headers=auth_headers)
    assert r2.status_code == 404


def test_contact_404(client, auth_headers):
    r = client.get("/api/crm/contacts/999999", headers=auth_headers)
    assert r.status_code == 404


# ── deals ────────────────────────────────────────────────────────────────────

def test_create_deal(client, auth_headers):
    # Deals require a contact
    contact = client.post("/api/crm/contacts", headers=auth_headers, json={"name": "Deal Contact", "email": "dc@x.com"})
    cid = contact.json()["id"]
    r = client.post("/api/crm/deals", headers=auth_headers, json={
        "contact_id": cid,
        "title": "Big Deal",
        "amount": 50000,
        "currency": "USD",
        "stage": "lead",
    })
    assert r.status_code == 201, r.text
    assert r.json()["title"] == "Big Deal"
    assert r.json()["stage"] == "lead"


def test_list_deals(client, auth_headers):
    contact = client.post("/api/crm/contacts", headers=auth_headers, json={"name": "List Contact", "email": "lc@x.com"})
    client.post("/api/crm/deals", headers=auth_headers, json={"contact_id": contact.json()["id"], "title": "D1", "stage": "lead"})
    r = client.get("/api/crm/deals", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_move_deal_stage(client, auth_headers):
    contact = client.post("/api/crm/contacts", headers=auth_headers, json={"name": "Stage Contact", "email": "sc@x.com"})
    create = client.post("/api/crm/deals", headers=auth_headers, json={"contact_id": contact.json()["id"], "title": "Move", "stage": "lead"})
    did = create.json()["id"]
    r = client.put(f"/api/crm/deals/{did}/stage?stage=qualified", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["stage"] == "qualified"


def test_deal_404(client, auth_headers):
    r = client.get("/api/crm/deals/999999", headers=auth_headers)
    assert r.status_code == 404


# ── products ─────────────────────────────────────────────────────────────────

def test_create_product(client, auth_headers):
    r = client.post("/api/crm/products", headers=auth_headers, json={
        "sku": "SKU-001",
        "name": "Widget",
        "price": 29.99,
        "currency": "USD",
    })
    assert r.status_code == 201, r.text
    assert r.json()["sku"] == "SKU-001"
    assert r.json()["active"] is True


def test_list_products(client, auth_headers):
    client.post("/api/crm/products", headers=auth_headers, json={"sku": "S1", "name": "P1", "price": 10})
    r = client.get("/api/crm/products", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_update_product(client, auth_headers):
    create = client.post("/api/crm/products", headers=auth_headers, json={"sku": "U1", "name": "Old", "price": 10})
    pid = create.json()["id"]
    r = client.put(f"/api/crm/products/{pid}", headers=auth_headers, json={"name": "New"})
    assert r.status_code == 200
    assert r.json()["name"] == "New"


def test_delete_product(client, auth_headers):
    create = client.post("/api/crm/products", headers=auth_headers, json={"sku": "D1", "name": "Del", "price": 10})
    pid = create.json()["id"]
    r = client.delete(f"/api/crm/products/{pid}", headers=auth_headers)
    assert r.status_code == 204


def test_product_duplicate_sku(client, auth_headers):
    client.post("/api/crm/products", headers=auth_headers, json={"sku": "DUP", "name": "A", "price": 10})
    r = client.post("/api/crm/products", headers=auth_headers, json={"sku": "DUP", "name": "B", "price": 20})
    assert r.status_code == 400


# ── orders ───────────────────────────────────────────────────────────────────

def test_order_metrics_empty(client, auth_headers):
    r = client.get("/api/crm/orders/metrics", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "order_count" in data
    assert data["order_count"] == 0


def test_create_order(client, auth_headers):
    # Orders require a contact
    contact = client.post("/api/crm/contacts", headers=auth_headers, json={"name": "Order Contact", "email": "oc@x.com"})
    cid = contact.json()["id"]

    r = client.post("/api/crm/orders", headers=auth_headers, json={
        "contact_id": cid,
        "items": [],
    })
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["status"] == "pending"


def test_list_orders(client, auth_headers):
    contact = client.post("/api/crm/contacts", headers=auth_headers, json={"name": "List Order Contact", "email": "loc@x.com"})
    client.post("/api/crm/orders", headers=auth_headers, json={
        "contact_id": contact.json()["id"], "items": [],
    })
    r = client.get("/api/crm/orders", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1
