# NOTICE: This file is protected under RCF-PL
"""Comprehensive tests for CRM routers.

Covers contacts, deals, products, orders, and activities CRUD + edge cases.
"""
from io import BytesIO
from types import SimpleNamespace

from openpyxl import Workbook

import app.routers.crm_activities as crm_activities_router


# ── helpers ──────────────────────────────────────────────────────────────────

def _create_contact(client, auth_headers, **overrides):
    data = {"name": "Test Contact", "email": "test@crm.com", **overrides}
    r = client.post("/api/crm/contacts", headers=auth_headers, json=data)
    assert r.status_code == 201, r.text
    return r.json()


def _create_deal(client, auth_headers, contact_id, **overrides):
    data = {"contact_id": contact_id, "title": "Test Deal", "stage": "lead", **overrides}
    r = client.post("/api/crm/deals", headers=auth_headers, json=data)
    assert r.status_code == 201, r.text
    return r.json()


def _create_product(client, auth_headers, **overrides):
    data = {"sku": "SKU-TEST", "name": "Test Product", "price": 99.99, **overrides}
    r = client.post("/api/crm/products", headers=auth_headers, json=data)
    assert r.status_code == 201, r.text
    return r.json()


# ── contacts ─────────────────────────────────────────────────────────────────

class TestContacts:
    def test_list_empty(self, client, auth_headers):
        r = client.get("/api/crm/contacts", headers=auth_headers)
        assert r.status_code == 200
        assert r.json() == []

    def test_create_and_get(self, client, auth_headers):
        c = _create_contact(client, auth_headers, name="Alice", email="alice@x.com")
        r = client.get(f"/api/crm/contacts/{c['id']}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["name"] == "Alice"

    def test_update(self, client, auth_headers):
        c = _create_contact(client, auth_headers)
        r = client.put(f"/api/crm/contacts/{c['id']}", headers=auth_headers, json={"name": "Updated"})
        assert r.status_code == 200
        assert r.json()["name"] == "Updated"

    def test_delete(self, client, auth_headers):
        c = _create_contact(client, auth_headers)
        r = client.delete(f"/api/crm/contacts/{c['id']}", headers=auth_headers)
        assert r.status_code == 204
        r2 = client.get(f"/api/crm/contacts/{c['id']}", headers=auth_headers)
        assert r2.status_code == 404

    def test_404(self, client, auth_headers):
        r = client.get("/api/crm/contacts/999999", headers=auth_headers)
        assert r.status_code == 404

    def test_search(self, client, auth_headers):
        _create_contact(client, auth_headers, name="Searchable", email="search@x.com")
        r = client.get("/api/crm/contacts?search=Searchable", headers=auth_headers)
        assert r.status_code == 200
        assert any("Searchable" in c["name"] for c in r.json())

    def test_import_contacts(self, client, auth_headers):
        wb = Workbook()
        ws = wb.active
        ws.append(["name", "email"])
        ws.append(["Import1", "imp1@x.com"])
        ws.append(["Import2", "imp2@x.com"])

        payload = BytesIO()
        wb.save(payload)

        r = client.post(
            "/api/crm/contacts/import",
            headers=auth_headers,
            files={
                "file": (
                    "contacts.xlsx",
                    payload.getvalue(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

        assert r.status_code == 201, r.text
        body = r.json()
        assert body["created"] == 2
        assert body["skipped"] == 0
        assert body["total_rows"] == 2

    def test_export_contacts(self, client, auth_headers):
        _create_contact(client, auth_headers, name="Exportable")
        r = client.get("/api/crm/contacts/export", headers=auth_headers)
        assert r.status_code == 200

    def test_contact_activities(self, client, auth_headers):
        c = _create_contact(client, auth_headers)
        r = client.get(f"/api/crm/contacts/{c['id']}/activities", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_contact_deals(self, client, auth_headers):
        c = _create_contact(client, auth_headers)
        r = client.get(f"/api/crm/contacts/{c['id']}/deals", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ── deals ────────────────────────────────────────────────────────────────────

class TestDeals:
    def test_create_deal(self, client, auth_headers):
        c = _create_contact(client, auth_headers)
        d = _create_deal(client, auth_headers, c["id"])
        assert d["stage"] == "lead"

    def test_list_deals(self, client, auth_headers):
        c = _create_contact(client, auth_headers)
        _create_deal(client, auth_headers, c["id"])
        r = client.get("/api/crm/deals", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_get_deal(self, client, auth_headers):
        c = _create_contact(client, auth_headers)
        d = _create_deal(client, auth_headers, c["id"])
        r = client.get(f"/api/crm/deals/{d['id']}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["title"] == "Test Deal"

    def test_update_deal(self, client, auth_headers):
        c = _create_contact(client, auth_headers)
        d = _create_deal(client, auth_headers, c["id"])
        r = client.put(f"/api/crm/deals/{d['id']}", headers=auth_headers, json={"title": "Updated Deal"})
        assert r.status_code == 200
        assert r.json()["title"] == "Updated Deal"

    def test_move_stage(self, client, auth_headers):
        c = _create_contact(client, auth_headers)
        d = _create_deal(client, auth_headers, c["id"])
        r = client.put(f"/api/crm/deals/{d['id']}/stage?stage=qualified", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["stage"] == "qualified"

    def test_delete_deal(self, client, auth_headers):
        c = _create_contact(client, auth_headers)
        d = _create_deal(client, auth_headers, c["id"])
        r = client.delete(f"/api/crm/deals/{d['id']}", headers=auth_headers)
        assert r.status_code == 204

    def test_deal_404(self, client, auth_headers):
        r = client.get("/api/crm/deals/999999", headers=auth_headers)
        assert r.status_code == 404


# ── products ─────────────────────────────────────────────────────────────────

class TestProducts:
    def test_create_product(self, client, auth_headers):
        p = _create_product(client, auth_headers, sku="P-001", name="Widget")
        assert p["sku"] == "P-001"
        assert p["active"] is True

    def test_list_products(self, client, auth_headers):
        _create_product(client, auth_headers, sku="L-001")
        r = client.get("/api/crm/products", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_get_product(self, client, auth_headers):
        p = _create_product(client, auth_headers, sku="G-001")
        r = client.get(f"/api/crm/products/{p['id']}", headers=auth_headers)
        assert r.status_code == 200

    def test_update_product(self, client, auth_headers):
        p = _create_product(client, auth_headers, sku="U-001")
        r = client.put(f"/api/crm/products/{p['id']}", headers=auth_headers, json={"name": "New Name"})
        assert r.status_code == 200
        assert r.json()["name"] == "New Name"

    def test_delete_product(self, client, auth_headers):
        p = _create_product(client, auth_headers, sku="D-001")
        r = client.delete(f"/api/crm/products/{p['id']}", headers=auth_headers)
        assert r.status_code == 204

    def test_duplicate_sku(self, client, auth_headers):
        _create_product(client, auth_headers, sku="DUP")
        r = client.post("/api/crm/products", headers=auth_headers, json={"sku": "DUP", "name": "B", "price": 20})
        assert r.status_code == 400

    def test_product_404(self, client, auth_headers):
        r = client.get("/api/crm/products/999999", headers=auth_headers)
        assert r.status_code == 404


# ── orders ───────────────────────────────────────────────────────────────────

class TestOrders:
    def test_metrics_empty(self, client, auth_headers):
        r = client.get("/api/crm/orders/metrics", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["order_count"] == 0

    def test_create_order(self, client, auth_headers):
        c = _create_contact(client, auth_headers)
        r = client.post("/api/crm/orders", headers=auth_headers, json={"contact_id": c["id"], "items": []})
        assert r.status_code == 201
        assert r.json()["status"] == "pending"

    def test_list_orders(self, client, auth_headers):
        c = _create_contact(client, auth_headers)
        client.post("/api/crm/orders", headers=auth_headers, json={"contact_id": c["id"], "items": []})
        r = client.get("/api/crm/orders", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_get_order(self, client, auth_headers):
        c = _create_contact(client, auth_headers)
        create = client.post("/api/crm/orders", headers=auth_headers, json={"contact_id": c["id"], "items": []})
        oid = create.json()["id"]
        r = client.get(f"/api/crm/orders/{oid}", headers=auth_headers)
        assert r.status_code == 200

    def test_update_order(self, client, auth_headers):
        c = _create_contact(client, auth_headers)
        create = client.post("/api/crm/orders", headers=auth_headers, json={"contact_id": c["id"], "items": []})
        oid = create.json()["id"]
        r = client.put(f"/api/crm/orders/{oid}", headers=auth_headers, json={"notes": "updated"})
        assert r.status_code == 200

    def test_status_transition(self, client, auth_headers):
        c = _create_contact(client, auth_headers)
        create = client.post(
            "/api/crm/orders",
            headers=auth_headers,
            json={"contact_id": c["id"], "items": []},
        )
        assert create.status_code == 201, create.text

        oid = create.json()["id"]
        r = client.put(
            f"/api/crm/orders/{oid}/status?status=processing",
            headers=auth_headers,
        )

        assert r.status_code == 200, r.text
        assert r.json()["status"] == "processing"

    def test_invalid_status_transition(self, client, auth_headers):
        c = _create_contact(
            client,
            auth_headers,
            name="Invalid Transition",
            email="invalid-transition@x.com",
        )
        create = client.post(
            "/api/crm/orders",
            headers=auth_headers,
            json={"contact_id": c["id"], "items": []},
        )
        assert create.status_code == 201, create.text

        oid = create.json()["id"]
        r = client.put(
            f"/api/crm/orders/{oid}/status?status=delivered",
            headers=auth_headers,
        )

        assert r.status_code == 400
        assert "Cannot move order" in r.json()["detail"]

    def test_order_history(self, client, auth_headers):
        c = _create_contact(client, auth_headers)
        create = client.post("/api/crm/orders", headers=auth_headers, json={"contact_id": c["id"], "items": []})
        oid = create.json()["id"]
        r = client.get(f"/api/crm/orders/{oid}/history", headers=auth_headers)
        assert r.status_code == 200

    def test_delete_order(self, client, auth_headers):
        c = _create_contact(client, auth_headers)
        create = client.post("/api/crm/orders", headers=auth_headers, json={"contact_id": c["id"], "items": []})
        oid = create.json()["id"]
        r = client.delete(f"/api/crm/orders/{oid}", headers=auth_headers)
        assert r.status_code == 204

    def test_order_404(self, client, auth_headers):
        r = client.get("/api/crm/orders/999999", headers=auth_headers)
        assert r.status_code == 404


# ── activities ───────────────────────────────────────────────────────────────

class TestActivities:
    def test_list_empty(self, client, auth_headers):
        r = client.get("/api/crm/activities", headers=auth_headers)
        assert r.status_code == 200
        assert r.json() == []

    def test_create_activity(self, client, auth_headers):
        c = _create_contact(client, auth_headers)
        r = client.post(
            "/api/crm/activities",
            headers=auth_headers,
            json={
                "contact_id": c["id"],
                "type": "call",
                "subject": "Follow up",
            },
        )

        assert r.status_code == 201, r.text
        body = r.json()
        assert body["contact_id"] == c["id"]
        assert body["type"] == "call"
        assert body["subject"] == "Follow up"

    def test_update_activity(self, client, auth_headers):
        first = _create_contact(
            client,
            auth_headers,
            name="Activity Contact One",
            email="activity-one@x.com",
        )
        second = _create_contact(
            client,
            auth_headers,
            name="Activity Contact Two",
            email="activity-two@x.com",
        )

        create = client.post(
            "/api/crm/activities",
            headers=auth_headers,
            json={
                "contact_id": first["id"],
                "type": "email_in",
                "subject": "Initial",
            },
        )
        assert create.status_code == 201, create.text

        aid = create.json()["id"]
        r = client.patch(
            f"/api/crm/activities/{aid}",
            headers=auth_headers,
            json={"contact_id": second["id"]},
        )

        assert r.status_code == 200, r.text
        assert r.json()["contact_id"] == second["id"]
        assert r.json()["subject"] == "Initial"

    def test_suggest_reply_rejects_non_inbound_activity(
        self,
        client,
        auth_headers,
    ):
        c = _create_contact(client, auth_headers)
        create = client.post(
            "/api/crm/activities",
            headers=auth_headers,
            json={
                "contact_id": c["id"],
                "type": "note",
                "subject": "Internal note",
            },
        )
        assert create.status_code == 201, create.text

        aid = create.json()["id"]
        r = client.post(
            f"/api/crm/activities/{aid}/suggest-reply",
            headers=auth_headers,
        )

        assert r.status_code == 400
        assert (
            r.json()["detail"]
            == "Can only suggest replies for inbound messages"
        )

    def _create_inbound_activity(self, client, auth_headers):
        c = _create_contact(
            client,
            auth_headers,
            name="Inbound Client",
            email="inbound@x.com",
        )
        create = client.post(
            "/api/crm/activities",
            headers=auth_headers,
            json={
                "contact_id": c["id"],
                "type": "email_in",
                "subject": "Question from client",
                "content": "Hi, when will my order ship?",
            },
        )
        assert create.status_code == 201, create.text
        return create.json()["id"]

    def test_suggest_reply_inbound_returns_draft(
        self,
        client,
        auth_headers,
        monkeypatch,
    ):
        fake_agent = SimpleNamespace(
            id=42,
            name="Support Bot",
            system_prompt="You are a helpful support agent.",
        )
        captured = {}

        async def fake_pick_agent(db, user, activity):
            return fake_agent

        async def fake_run_agent(db, agent, messages, extras=None):
            captured["agent"] = agent
            captured["messages"] = messages
            captured["extras"] = extras
            return "  Your order ships tomorrow.  "

        monkeypatch.setattr(crm_activities_router, "_pick_agent", fake_pick_agent)
        monkeypatch.setattr(crm_activities_router, "run_agent", fake_run_agent)

        aid = self._create_inbound_activity(client, auth_headers)
        r = client.post(
            f"/api/crm/activities/{aid}/suggest-reply",
            headers=auth_headers,
        )

        assert r.status_code == 200, r.text
        body = r.json()
        assert body["draft"] == "Your order ships tomorrow."
        assert body["agent_id"] == 42
        assert body["agent_name"] == "Support Bot"

        assert captured["agent"] is fake_agent
        assert captured["extras"] == {"mode": "suggest_reply"}
        assert captured["messages"][0] == {
            "role": "system",
            "content": "You are a helpful support agent.",
        }
        user_prompt = captured["messages"][1]["content"]
        assert "Question from client" in user_prompt
        assert "when will my order ship?" in user_prompt
        assert "Inbound Client" in user_prompt

    def test_suggest_reply_without_agent(
        self,
        client,
        auth_headers,
        monkeypatch,
    ):
        async def no_agent(db, user, activity):
            return None

        monkeypatch.setattr(crm_activities_router, "_pick_agent", no_agent)

        aid = self._create_inbound_activity(client, auth_headers)
        r = client.post(
            f"/api/crm/activities/{aid}/suggest-reply",
            headers=auth_headers,
        )

        assert r.status_code == 400
        assert r.json()["detail"] == "No agent available to draft a reply"
