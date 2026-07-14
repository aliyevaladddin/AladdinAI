# NOTICE: This file is protected under RCF-PL
"""Order & sales agent tools.

Read tools (list/summary/metrics) go in the `_default` tool set so any agent
can answer questions about orders. Write tools (create_order, update_order_status,
create_product) are gated behind the `"sales"` role in DEFAULT_TOOLS_BY_ROLE —
only a sales agent may mutate the order book.

All work is scoped to `ctx.user_id`. Status changes made by an agent are logged
to the CRM timeline with `agent_id=ctx.agent_id` so the history shows who moved it.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.contact import Contact
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.services.crm_service import (
    ALLOWED_TRANSITIONS,
    ORDER_STATUSES,
    can_transition,
    find_or_create_contact,
    log_order_status_change,
    recompute_order_total,
)
from app.tools.base import ToolContext, tool


# ── read tools (available to every agent) ────────────────────────────────────
@tool(
    name="list_orders",
    description="List the current user's orders, optionally filtered by status "
                "(pending, processing, shipped, delivered, cancelled). Returns id, "
                "contact, status, total and item count for each.",
    parameters={
        "type": "object",
        "properties": {
            "status": {"type": "string", "description": "Filter by order status"},
            "limit": {"type": "integer", "description": "Max orders to return (default 20)"},
        },
    },
)
async def list_orders(ctx: ToolContext, status: str | None = None, limit: int = 20) -> dict[str, Any]:
    q = select(Order).options(selectinload(Order.items)).where(Order.user_id == ctx.user_id)
    if status:
        q = q.where(Order.status == status)
    q = q.order_by(Order.created_at.desc()).limit(min(limit, 100))
    result = await ctx.db.execute(q)
    orders = result.scalars().all()
    return {
        "count": len(orders),
        "orders": [
            {
                "id": o.id,
                "contact_id": o.contact_id,
                "status": o.status,
                "total": o.total,
                "currency": o.currency,
                "item_count": len(o.items),
            }
            for o in orders
        ],
    }


@tool(
    name="get_order_summary",
    description="Get the full detail of one order by id: status, total, and every line item.",
    parameters={
        "type": "object",
        "properties": {"order_id": {"type": "integer"}},
        "required": ["order_id"],
    },
)
async def get_order_summary(ctx: ToolContext, order_id: int) -> dict[str, Any]:
    result = await ctx.db.execute(
        select(Order).options(selectinload(Order.items))
        .where(Order.id == order_id, Order.user_id == ctx.user_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        return {"error": f"Order {order_id} not found"}
    return {
        "id": order.id,
        "contact_id": order.contact_id,
        "status": order.status,
        "total": order.total,
        "currency": order.currency,
        "source": order.source,
        "campaign": order.campaign,
        "items": [
            {"product_name": i.product_name, "quantity": i.quantity,
             "unit_price": i.unit_price, "line_total": i.line_total}
            for i in order.items
        ],
    }


@tool(
    name="get_sales_metrics",
    description="Get sales KPIs for the current user: realized revenue (delivered orders), "
                "booked revenue (non-cancelled), order count, and a breakdown by status.",
    parameters={"type": "object", "properties": {}},
)
async def get_sales_metrics(ctx: ToolContext) -> dict[str, Any]:
    rows = await ctx.db.execute(
        select(Order.status, func.count(Order.id), func.coalesce(func.sum(Order.total), 0.0))
        .where(Order.user_id == ctx.user_id)
        .group_by(Order.status)
    )
    count_by_status = {s: 0 for s in ORDER_STATUSES}
    revenue_by_status = {s: 0.0 for s in ORDER_STATUSES}
    realized = booked = 0.0
    total_count = 0
    for status, cnt, rev in rows.all():
        count_by_status[status] = cnt
        revenue_by_status[status] = round(float(rev), 2)
        total_count += cnt
        if status == "delivered":
            realized += float(rev)
        if status != "cancelled":
            booked += float(rev)
    return {
        "realized_revenue": round(realized, 2),
        "booked_revenue": round(booked, 2),
        "order_count": total_count,
        "count_by_status": count_by_status,
        "revenue_by_status": revenue_by_status,
    }


# ── write tools (sales role only) ────────────────────────────────────────────
@tool(
    name="create_order",
    description="Create a new order for a customer. Identify the customer by contact_id, "
                "or by email/phone (a contact is created if none exists). Each item is a "
                "product (by sku or product_id) with a quantity. Returns the created order id and total.",
    parameters={
        "type": "object",
        "properties": {
            "contact_id": {"type": "integer", "description": "Existing contact id"},
            "email": {"type": "string", "description": "Customer email (used if contact_id omitted)"},
            "phone": {"type": "string", "description": "Customer phone (used if contact_id and email omitted)"},
            "name": {"type": "string", "description": "Customer name when creating a new contact"},
            "items": {
                "type": "array",
                "description": "Line items",
                "items": {
                    "type": "object",
                    "properties": {
                        "sku": {"type": "string"},
                        "product_id": {"type": "integer"},
                        "product_name": {"type": "string"},
                        "quantity": {"type": "integer"},
                        "unit_price": {"type": "number"},
                    },
                },
            },
            "source": {"type": "string", "description": "Marketing attribution source"},
            "campaign": {"type": "string", "description": "Marketing campaign name"},
            "notes": {"type": "string"},
        },
        "required": ["items"],
    },
)
async def create_order(
    ctx: ToolContext,
    items: list[dict],
    contact_id: int | None = None,
    email: str | None = None,
    phone: str | None = None,
    name: str = "",
    source: str | None = None,
    campaign: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    # Resolve the contact.
    if contact_id is not None:
        res = await ctx.db.execute(
            select(Contact).where(Contact.id == contact_id, Contact.user_id == ctx.user_id)
        )
        if not res.scalar_one_or_none():
            return {"error": f"Contact {contact_id} not found"}
    elif email or phone:
        contact = await find_or_create_contact(
            ctx.db, ctx.user_id,
            identifier=(phone if (phone and not email) else email),
            name=name, source=source or "agent_order", is_phone=bool(phone and not email),
        )
        contact_id = contact.id
    else:
        return {"error": "Provide contact_id, email, or phone to identify the customer"}

    if not items:
        return {"error": "An order needs at least one item"}

    order = Order(
        user_id=ctx.user_id,
        contact_id=contact_id,
        assigned_agent_id=ctx.agent_id,
        source=source,
        campaign=campaign,
        notes=notes,
        status="pending",
        total=0.0,
    )
    for spec in items:
        product_id = spec.get("product_id")
        product_name = spec.get("product_name")
        unit_price = spec.get("unit_price")
        sku = spec.get("sku")
        # Resolve product by explicit id or by sku.
        product = None
        if product_id is not None:
            r = await ctx.db.execute(
                select(Product).where(Product.id == product_id, Product.user_id == ctx.user_id)
            )
            product = r.scalar_one_or_none()
        elif sku:
            r = await ctx.db.execute(
                select(Product).where(Product.sku == sku, Product.user_id == ctx.user_id)
            )
            product = r.scalar_one_or_none()
        if product is not None:
            product_id = product.id
            product_name = product_name or product.name
            if unit_price is None:
                unit_price = product.price
        if not product_name:
            return {"error": f"Could not resolve a product for item {spec}. Provide a valid sku, product_id, or product_name."}
        qty = int(spec.get("quantity") or 1)
        if qty <= 0:
            return {"error": f"Invalid quantity {qty}. Quantity must be greater than 0."}
        unit_price = float(unit_price or 0.0)
        if unit_price < 0.0:
            return {"error": f"Invalid unit price {unit_price}. Price must be non-negative."}
        order.items.append(OrderItem(
            product_id=product_id,
            product_name=product_name,
            quantity=qty,
            unit_price=unit_price,
            line_total=round(unit_price * qty, 2),
        ))
    recompute_order_total(order)
    ctx.db.add(order)
    await ctx.db.commit()
    await ctx.db.refresh(order)
    return {
        "order_id": order.id,
        "contact_id": order.contact_id,
        "status": order.status,
        "total": order.total,
        "message": f"Created order #{order.id} totalling {order.total} {order.currency}.",
    }


@tool(
    name="update_order_status",
    description="Move an order to a new status. Legal moves: pending→processing→shipped→delivered; "
                "any non-terminal status may go to cancelled. delivered and cancelled are final.",
    parameters={
        "type": "object",
        "properties": {
            "order_id": {"type": "integer"},
            "status": {"type": "string", "description": "Target status"},
        },
        "required": ["order_id", "status"],
    },
)
async def update_order_status(ctx: ToolContext, order_id: int, status: str) -> dict[str, Any]:
    if status not in ORDER_STATUSES:
        return {"error": f"Invalid status. Must be one of: {ORDER_STATUSES}"}
    result = await ctx.db.execute(
        select(Order).options(selectinload(Order.items))
        .where(Order.id == order_id, Order.user_id == ctx.user_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        return {"error": f"Order {order_id} not found"}
    old_status = order.status
    if status == old_status:
        return {"order_id": order.id, "status": status, "message": "No change."}
    if not can_transition(old_status, status):
        allowed = ALLOWED_TRANSITIONS.get(old_status, [])
        return {"error": f"Cannot move order from '{old_status}' to '{status}'. Allowed: {allowed or 'none (terminal)'}"}
    order.status = status
    await log_order_status_change(ctx.db, ctx.user_id, order, old_status, status, agent_id=ctx.agent_id)
    await ctx.db.commit()
    return {
        "order_id": order.id,
        "old_status": old_status,
        "new_status": status,
        "message": f"Order #{order.id} moved from {old_status} to {status}.",
    }


@tool(
    name="create_product",
    description="Add a product to the catalog (sku, name, price). SKU must be unique for the user.",
    parameters={
        "type": "object",
        "properties": {
            "sku": {"type": "string"},
            "name": {"type": "string"},
            "price": {"type": "number"},
            "currency": {"type": "string"},
            "description": {"type": "string"},
        },
        "required": ["sku", "name"],
    },
)
async def create_product(
    ctx: ToolContext,
    sku: str,
    name: str,
    price: float = 0.0,
    currency: str = "USD",
    description: str | None = None,
) -> dict[str, Any]:
    dup = await ctx.db.execute(
        select(Product).where(Product.user_id == ctx.user_id, Product.sku == sku)
    )
    if dup.scalar_one_or_none():
        return {"error": f"SKU '{sku}' already exists"}
    product = Product(
        user_id=ctx.user_id, sku=sku, name=name, price=price,
        currency=currency, description=description,
    )
    ctx.db.add(product)
    await ctx.db.commit()
    await ctx.db.refresh(product)
    return {"product_id": product.id, "sku": product.sku, "name": product.name, "price": product.price}
