# NOTICE: This file is protected under RCF-PL
"""Tests for CRM agent tools:

- create_contact
- create_contacts_batch (e.g. importing 20 clients)
- list_contacts & get_contact
- create_deal & list_deals & update_deal_stage
- User scoping
- Schema export via REGISTRY / openai_schemas
"""
import pytest
from app.tools.base import ToolContext, execute, openai_schemas


@pytest.mark.asyncio
async def test_crm_tools_registered():
    """Verify all CRM tools are present in REGISTRY and openai_schemas."""
    schemas = openai_schemas([
        "create_contact", "create_contacts_batch", "list_contacts", "get_contact",
        "create_deal", "create_deals_batch", "list_deals", "update_deal_stage",
    ])
    names = {s["function"]["name"] for s in schemas}
    assert "create_contact" in names
    assert "create_contacts_batch" in names
    assert "list_contacts" in names
    assert "get_contact" in names
    assert "create_deal" in names
    assert "create_deals_batch" in names
    assert "list_deals" in names
    assert "update_deal_stage" in names


@pytest.mark.asyncio
async def test_tool_create_contact(test_user, db_session):
    uid = test_user["user_id"]
    ctx = ToolContext(db=db_session, user_id=uid, agent_id=1)

    result = await execute("create_contact", {
        "name": "Alice Wonderland",
        "email": "alice@example.com",
        "phone": "+1987654321",
        "company": "Wonderland LLC",
        "tags": ["vip", "client"],
        "notes": "First client created via agent tool",
    }, ctx)

    assert result.get("status") == "created"
    contact = result.get("contact", {})
    assert contact.get("name") == "Alice Wonderland"
    assert contact.get("email") == "alice@example.com"
    assert contact.get("company") == "Wonderland LLC"
    assert "id" in contact

    # Fetch with get_contact
    fetched = await execute("get_contact", {"contact_id": contact["id"]}, ctx)
    assert fetched.get("name") == "Alice Wonderland"
    assert fetched.get("company") == "Wonderland LLC"


@pytest.mark.asyncio
async def test_tool_create_contact_validation(test_user, db_session):
    uid = test_user["user_id"]
    ctx = ToolContext(db=db_session, user_id=uid)

    res = await execute("create_contact", {"name": "   "}, ctx)
    assert "error" in res


@pytest.mark.asyncio
async def test_tool_create_contacts_batch_20(test_user, db_session):
    """Test importing 20 clients in a single tool call."""
    uid = test_user["user_id"]
    ctx = ToolContext(db=db_session, user_id=uid, agent_id=2)

    clients = [
        {
            "name": f"Client #{i}",
            "email": f"client_{i}@corp.az",
            "company": f"Corp {i}",
            "tags": ["batch_import", f"group_{i % 3}"],
        }
        for i in range(1, 21)
    ]

    result = await execute("create_contacts_batch", {"contacts": clients}, ctx)
    assert result.get("status") == "success"
    assert result.get("created_count") == 20
    assert len(result.get("contacts", [])) == 20
    assert result.get("errors") == []

    # Verify search and listing
    listing = await execute("list_contacts", {"search": "Corp 15"}, ctx)
    assert listing.get("count") == 1
    assert listing["contacts"][0]["name"] == "Client #15"


@pytest.mark.asyncio
async def test_tool_list_contacts_search_and_tag(test_user, db_session):
    uid = test_user["user_id"]
    ctx = ToolContext(db=db_session, user_id=uid)

    await execute("create_contact", {"name": "Bob Target", "email": "bob@target.com", "tags": ["target"]}, ctx)
    await execute("create_contact", {"name": "Charlie Other", "email": "charlie@other.com"}, ctx)

    # Search by text
    res = await execute("list_contacts", {"search": "Target"}, ctx)
    assert res.get("count") == 1
    assert res["contacts"][0]["name"] == "Bob Target"

    # Search by tag
    res_tag = await execute("list_contacts", {"tag": "target"}, ctx)
    assert res_tag.get("count") == 1
    assert res_tag["contacts"][0]["name"] == "Bob Target"


@pytest.mark.asyncio
async def test_tool_create_deal_and_update_stage(test_user, db_session):
    uid = test_user["user_id"]
    ctx = ToolContext(db=db_session, user_id=uid, agent_id=3)

    # Create deal with auto-created contact via email
    deal_res = await execute("create_deal", {
        "title": "Cloud Migration",
        "email": "cio@enterprise.com",
        "name": "CIO John",
        "amount": 50000.0,
        "stage": "qualified",
        "probability": 60,
    }, ctx)

    assert deal_res.get("status") == "created"
    deal = deal_res.get("deal", {})
    deal_id = deal.get("id")
    assert deal.get("title") == "Cloud Migration"
    assert deal.get("amount") == 50000.0
    assert deal.get("stage") == "qualified"

    # List deals
    deals_list = await execute("list_deals", {"stage": "qualified"}, ctx)
    assert any(d["id"] == deal_id for d in deals_list.get("deals", []))

    # Move stage to won
    moved = await execute("update_deal_stage", {
        "deal_id": deal_id,
        "stage": "won",
        "notes": "Contract signed!",
    }, ctx)
    assert moved.get("status") == "updated"
    assert moved.get("new_stage") == "won"

    # Reject invalid stage
    invalid = await execute("update_deal_stage", {
        "deal_id": deal_id,
        "stage": "unknown_stage",
    }, ctx)
    assert "error" in invalid


@pytest.mark.asyncio
async def test_tool_create_deals_batch(test_user, db_session):
    uid = test_user["user_id"]
    ctx = ToolContext(db=db_session, user_id=uid, agent_id=4)

    # First create a contact
    c_res = await execute("create_contact", {"name": "Deal Batch Partner"}, ctx)
    cid = c_res["contact"]["id"]

    deals_payload = [
        {"title": "Deal A", "contact_id": cid, "amount": 100000.0, "stage": "lead"},
        {"title": "Deal B", "contact_id": cid, "amount": 250000.0, "stage": "proposal"},
        {"title": "Deal C", "contact_id": cid, "amount": 500000.0, "stage": "won"},
    ]
    res = await execute("create_deals_batch", {"deals": deals_payload}, ctx)
    assert res.get("status") == "success"
    assert res.get("created_count") == 3
    assert len(res.get("deals", [])) == 3
    assert res.get("errors") == []
    assert res["deals"][0]["title"] == "Deal A"


@pytest.mark.asyncio
async def test_tool_scoping_isolation(client, test_user, db_session):
    """User 2 cannot view or update User 1's contact/deal."""
    uid1 = test_user["user_id"]
    ctx1 = ToolContext(db=db_session, user_id=uid1)

    c1 = await execute("create_contact", {"name": "Private User 1 Contact"}, ctx1)
    cid = c1["contact"]["id"]

    # User 2 context
    ctx2 = ToolContext(db=db_session, user_id=99999)
    get_res = await execute("get_contact", {"contact_id": cid}, ctx2)
    assert "error" in get_res
