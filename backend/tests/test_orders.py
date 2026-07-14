# NOTICE: This file is protected under RCF-PL
"""Tests for the Orders + Products layer and the sales agent tools.

Two levels, mirroring test_crm.py + test_tools.py:
  * HTTP — products CRUD, order create/total, item recompute, price snapshot,
    status transition graph, history, metrics, scoping, auth.
  * tools — create_order / update_order_status via ToolContext against the DB.
"""
import asyncio

from app.tools.base import ToolContext, execute


# ── helpers ──────────────────────────────────────────────────────────────────
def _contact(client, headers, name="Buyer", email="buyer@example.com") -> int:
    r = client.post("/api/crm/contacts", headers=headers, json={"name": name, "email": email})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _product(client, headers, sku="SKU1", name="Widget", price=10.0) -> int:
    r = client.post("/api/crm/products", headers=headers, json={"sku": sku, "name": name, "price": price})
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ── products ─────────────────────────────────────────────────────────────────
def test_create_product(client, auth_headers):
    r = client.post("/api/crm/products", headers=auth_headers,
                    json={"sku": "ABC", "name": "Thing", "price": 5.5})
    assert r.status_code == 201
    data = r.json()
    assert data["sku"] == "ABC" and data["price"] == 5.5 and data["active"] is True


def test_create_product_duplicate_sku_400(client, auth_headers):
    client.post("/api/crm/products", headers=auth_headers, json={"sku": "DUP", "name": "A"})
    r = client.post("/api/crm/products", headers=auth_headers, json={"sku": "DUP", "name": "B"})
    assert r.status_code == 400


def test_list_products(client, auth_headers):
    _product(client, auth_headers, sku="P1", name="One")
    _product(client, auth_headers, sku="P2", name="Two")
    r = client.get("/api/crm/products", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_product_scoping_404(client, test_user):
    u2 = client.post("/api/auth/register",
                     json={"email": "prod2@example.com", "password": "password123", "name": "U2"})
    h2 = {"Authorization": f"Bearer {u2.json()['access_token']}"}
    h1 = {"Authorization": f"Bearer {test_user['token']}"}
    pid = _product(client, h1, sku="PRIV")
    assert client.get(f"/api/crm/products/{pid}", headers=h2).status_code == 404


# ── orders: create + total ───────────────────────────────────────────────────
def test_create_order_computes_total(client, auth_headers):
    cid = _contact(client, auth_headers)
    p1 = _product(client, auth_headers, sku="A", name="A", price=10.0)
    p2 = _product(client, auth_headers, sku="B", name="B", price=2.5)
    r = client.post("/api/crm/orders", headers=auth_headers, json={
        "contact_id": cid,
        "items": [
            {"product_id": p1, "quantity": 3},   # 30
            {"product_id": p2, "quantity": 2},    # 5
        ],
    })
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["status"] == "pending"
    assert data["total"] == 35.0
    assert len(data["items"]) == 2
    assert {i["product_name"] for i in data["items"]} == {"A", "B"}


def test_order_item_add_update_delete_recompute(client, auth_headers):
    cid = _contact(client, auth_headers)
    p = _product(client, auth_headers, sku="X", price=10.0)
    oid = client.post("/api/crm/orders", headers=auth_headers,
                      json={"contact_id": cid, "items": [{"product_id": p, "quantity": 1}]}).json()["id"]

    # add item → +20
    r = client.post(f"/api/crm/orders/{oid}/items", headers=auth_headers,
                    json={"product_id": p, "quantity": 2})
    assert r.status_code == 201
    assert r.json()["total"] == 30.0
    item_id = r.json()["items"][-1]["id"]

    # update that item to qty 5 → line 50, total 60
    r = client.put(f"/api/crm/orders/{oid}/items/{item_id}", headers=auth_headers,
                   json={"product_id": p, "quantity": 5})
    assert r.status_code == 200
    assert r.json()["total"] == 60.0

    # delete it → back to 10
    r = client.delete(f"/api/crm/orders/{oid}/items/{item_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["total"] == 10.0


def test_order_price_snapshot_survives_product_edit(client, auth_headers):
    cid = _contact(client, auth_headers)
    p = _product(client, auth_headers, sku="SNAP", price=10.0)
    oid = client.post("/api/crm/orders", headers=auth_headers,
                      json={"contact_id": cid, "items": [{"product_id": p, "quantity": 1}]}).json()["id"]

    # Raise the catalog price after the order is placed.
    client.put(f"/api/crm/products/{p}", headers=auth_headers, json={"price": 999.0})

    data = client.get(f"/api/crm/orders/{oid}", headers=auth_headers).json()
    assert data["total"] == 10.0  # unchanged — the line snapshotted the old price
    assert data["items"][0]["unit_price"] == 10.0


def test_create_order_unknown_contact_404(client, auth_headers):
    r = client.post("/api/crm/orders", headers=auth_headers,
                    json={"contact_id": 999999, "items": []})
    assert r.status_code == 404


# ── status transitions ────────────────────────────────────────────────────────
def test_status_valid_transition(client, auth_headers):
    cid = _contact(client, auth_headers)
    oid = client.post("/api/crm/orders", headers=auth_headers,
                      json={"contact_id": cid, "items": []}).json()["id"]
    r = client.put(f"/api/crm/orders/{oid}/status?status=processing", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "processing"


def test_status_forbidden_transition_400(client, auth_headers):
    cid = _contact(client, auth_headers)
    oid = client.post("/api/crm/orders", headers=auth_headers,
                      json={"contact_id": cid, "items": []}).json()["id"]
    # deliver it (pending→processing→shipped→delivered)
    for s in ["processing", "shipped", "delivered"]:
        assert client.put(f"/api/crm/orders/{oid}/status?status={s}", headers=auth_headers).status_code == 200
    # delivered is terminal — cannot go back to pending
    r = client.put(f"/api/crm/orders/{oid}/status?status=pending", headers=auth_headers)
    assert r.status_code == 400


def test_status_invalid_value_400(client, auth_headers):
    cid = _contact(client, auth_headers)
    oid = client.post("/api/crm/orders", headers=auth_headers,
                      json={"contact_id": cid, "items": []}).json()["id"]
    r = client.put(f"/api/crm/orders/{oid}/status?status=teleported", headers=auth_headers)
    assert r.status_code == 400


def test_order_history_records_changes(client, auth_headers):
    cid = _contact(client, auth_headers)
    oid = client.post("/api/crm/orders", headers=auth_headers,
                      json={"contact_id": cid, "items": []}).json()["id"]
    client.put(f"/api/crm/orders/{oid}/status?status=processing", headers=auth_headers)
    client.put(f"/api/crm/orders/{oid}/status?status=cancelled", headers=auth_headers)

    hist = client.get(f"/api/crm/orders/{oid}/history", headers=auth_headers).json()
    assert len(hist) == 2
    pairs = {(h["old_status"], h["new_status"]) for h in hist}
    assert ("pending", "processing") in pairs
    assert ("processing", "cancelled") in pairs


# ── metrics ────────────────────────────────────────────────────────────────────
def test_order_metrics(client, auth_headers):
    cid = _contact(client, auth_headers)
    p = _product(client, auth_headers, sku="M", price=100.0)

    def _order(qty):
        return client.post("/api/crm/orders", headers=auth_headers,
                           json={"contact_id": cid, "items": [{"product_id": p, "quantity": qty}]}).json()["id"]

    delivered = _order(1)  # 100 → delivered
    for s in ["processing", "shipped", "delivered"]:
        client.put(f"/api/crm/orders/{delivered}/status?status={s}", headers=auth_headers)
    cancelled = _order(2)  # 200 → cancelled
    client.put(f"/api/crm/orders/{cancelled}/status?status=cancelled", headers=auth_headers)
    _order(3)  # 300 → stays pending

    # A won and a lost deal for funnel/pipeline.
    client.post("/api/crm/deals", headers=auth_headers,
                json={"contact_id": cid, "title": "won", "stage": "won", "amount": 500.0})
    client.post("/api/crm/deals", headers=auth_headers,
                json={"contact_id": cid, "title": "open", "stage": "proposal", "amount": 400.0})

    m = client.get("/api/crm/orders/metrics", headers=auth_headers).json()
    assert m["order_count"] == 3
    assert m["realized_revenue"] == 100.0            # only delivered
    assert m["booked_revenue"] == 400.0              # 100 + 300, cancelled excluded
    assert m["count_by_status"]["delivered"] == 1
    assert m["count_by_status"]["cancelled"] == 1
    assert m["pipeline_value"] == 400.0              # open proposal deal
    assert m["funnel"]["won"] == 1


def test_orders_mine_filter(client, auth_headers):
    cid = _contact(client, auth_headers)
    # unassigned
    client.post("/api/crm/orders", headers=auth_headers, json={"contact_id": cid, "items": []})
    # assigned to an agent id (FK not enforced on the nullable column in sqlite)
    client.post("/api/crm/orders", headers=auth_headers,
                json={"contact_id": cid, "assigned_agent_id": 1, "items": []})
    all_orders = client.get("/api/crm/orders", headers=auth_headers).json()
    mine = client.get("/api/crm/orders?mine=true", headers=auth_headers).json()
    assert len(all_orders) == 2
    assert len(mine) == 1 and mine[0]["assigned_agent_id"] == 1


def test_order_scoping_404(client, test_user):
    u2 = client.post("/api/auth/register",
                     json={"email": "ord2@example.com", "password": "password123", "name": "U2"})
    h2 = {"Authorization": f"Bearer {u2.json()['access_token']}"}
    h1 = {"Authorization": f"Bearer {test_user['token']}"}
    cid = _contact(client, h1)
    oid = client.post("/api/crm/orders", headers=h1, json={"contact_id": cid, "items": []}).json()["id"]
    assert client.get(f"/api/crm/orders/{oid}", headers=h2).status_code == 404


def test_orders_require_auth(client):
    assert client.get("/api/crm/orders").status_code == 401


# ── agent tools ────────────────────────────────────────────────────────────────
def test_tool_create_order_and_status(client, test_user, db_session):
    uid = test_user["user_id"]
    # seed a contact + product via API (same DB session the tool will use)
    h = {"Authorization": f"Bearer {test_user['token']}"}
    cid = _contact(client, h)
    _product(client, h, sku="TOOLSKU", name="ToolWidget", price=25.0)

    ctx = ToolContext(db=db_session, user_id=uid, agent_id=7)

    result = asyncio.get_event_loop().run_until_complete(
        execute("create_order", {
            "contact_id": cid,
            "items": [{"sku": "TOOLSKU", "quantity": 4}],
            "source": "agent",
        }, ctx)
    )
    assert "order_id" in result, result
    assert result["total"] == 100.0
    order_id = result["order_id"]

    # move status via tool; agent_id must be recorded in the history log
    moved = asyncio.get_event_loop().run_until_complete(
        execute("update_order_status", {"order_id": order_id, "status": "processing"}, ctx)
    )
    assert moved["new_status"] == "processing"

    hist = client.get(f"/api/crm/orders/{order_id}/history", headers=h).json()
    assert len(hist) == 1
    assert hist[0]["agent_id"] == 7


def test_tool_update_status_rejects_bad_transition(client, test_user, db_session):
    uid = test_user["user_id"]
    h = {"Authorization": f"Bearer {test_user['token']}"}
    cid = _contact(client, h)
    oid = client.post("/api/crm/orders", headers=h, json={"contact_id": cid, "items": []}).json()["id"]

    ctx = ToolContext(db=db_session, user_id=uid, agent_id=1)
    result = asyncio.get_event_loop().run_until_complete(
        execute("update_order_status", {"order_id": oid, "status": "delivered"}, ctx)
    )
    # pending → delivered is not a legal single hop
    assert "error" in result
