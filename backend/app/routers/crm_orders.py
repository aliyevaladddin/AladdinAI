# NOTICE: This file is protected under RCF-PL
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.activity import Activity
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User
from app.schemas.crm import (
    OrderCreate,
    OrderItemCreate,
    OrderMetricsResponse,
    OrderResponse,
    OrderUpdate,
)
from app.security import get_current_user
from app.services.crm_service import (
    ALLOWED_TRANSITIONS,
    ORDER_STATUSES,
    can_transition,
    log_order_status_change,
    recompute_order_total,
)

router = APIRouter(prefix="/crm/orders", tags=["crm"])

_OPEN_DEAL_STAGES = ["lead", "qualified", "proposal", "negotiation"]


# ── helpers ──────────────────────────────────────────────────────────────────
async def _get_order(db: AsyncSession, order_id: int, user_id: int) -> Order:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id, Order.user_id == user_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


async def _build_item(db: AsyncSession, user_id: int, spec: OrderItemCreate) -> OrderItem:
    """Resolve an item spec into an OrderItem, snapshotting name + price."""
    product_name = spec.product_name
    unit_price = spec.unit_price
    if spec.product_id is not None:
        res = await db.execute(
            select(Product).where(Product.id == spec.product_id, Product.user_id == user_id)
        )
        product = res.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {spec.product_id} not found")
        product_name = product_name or product.name
        if unit_price is None:
            unit_price = product.price
    if not product_name:
        raise HTTPException(status_code=400, detail="Each item needs a product_id or a product_name")
    unit_price = unit_price or 0.0
    qty = spec.quantity or 1
    return OrderItem(
        product_id=spec.product_id,
        product_name=product_name,
        quantity=qty,
        unit_price=unit_price,
        line_total=round(unit_price * qty, 2),
    )


_BACKGROUND_TASKS = set()


def _fire_webhook(user_id: int, event: str, payload: dict) -> None:
    from app.services.webhook_service import trigger_webhooks
    task = asyncio.create_task(trigger_webhooks(user_id, event, payload))
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)


# ── metrics (MUST be declared before /{order_id}) ────────────────────────────
# [RCF:PROTECTED]
@router.get("/metrics", response_model=OrderMetricsResponse)
# [RCF:PROTECTED]
async def order_metrics(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Sales + marketing dashboard numbers, all user-scoped."""
    # Orders grouped by status.
    rows = await db.execute(
        select(Order.status, func.count(Order.id), func.coalesce(func.sum(Order.total), 0.0))
        .where(Order.user_id == user.id)
        .group_by(Order.status)
    )
    count_by_status = {s: 0 for s in ORDER_STATUSES}
    revenue_by_status = {s: 0.0 for s in ORDER_STATUSES}
    order_count = 0
    realized_revenue = 0.0
    booked_revenue = 0.0
    for status, cnt, rev in rows.all():
        count_by_status[status] = cnt
        revenue_by_status[status] = round(float(rev), 2)
        order_count += cnt
        if status == "delivered":
            realized_revenue += float(rev)
        if status != "cancelled":
            booked_revenue += float(rev)

    # Deal funnel + open pipeline value.
    deal_rows = await db.execute(
        select(Deal.stage, func.count(Deal.id), func.coalesce(func.sum(Deal.amount), 0.0))
        .where(Deal.user_id == user.id)
        .group_by(Deal.stage)
    )
    funnel: dict[str, int] = {}
    pipeline_value = 0.0
    won = lost = 0
    for stage, cnt, amount in deal_rows.all():
        funnel[stage] = cnt
        if stage in _OPEN_DEAL_STAGES:
            pipeline_value += float(amount)
        if stage == "won":
            won = cnt
        if stage == "lost":
            lost = cnt
    win_rate = round(won / (won + lost), 4) if (won + lost) else 0.0

    # Marketing attribution.
    src_rows = await db.execute(
        select(Order.source, func.coalesce(func.sum(Order.total), 0.0))
        .where(Order.user_id == user.id, Order.status != "cancelled")
        .group_by(Order.source)
    )
    revenue_by_source = {(s or "unknown"): round(float(v), 2) for s, v in src_rows.all()}
    camp_rows = await db.execute(
        select(Order.campaign, func.coalesce(func.sum(Order.total), 0.0))
        .where(Order.user_id == user.id, Order.status != "cancelled")
        .group_by(Order.campaign)
    )
    revenue_by_campaign = {(c or "none"): round(float(v), 2) for c, v in camp_rows.all()}

    return OrderMetricsResponse(
        realized_revenue=round(realized_revenue, 2),
        booked_revenue=round(booked_revenue, 2),
        order_count=order_count,
        count_by_status=count_by_status,
        revenue_by_status=revenue_by_status,
        pipeline_value=round(pipeline_value, 2),
        funnel=funnel,
        win_rate=win_rate,
        revenue_by_source=revenue_by_source,
        revenue_by_campaign=revenue_by_campaign,
    )


# ── list + create ────────────────────────────────────────────────────────────
# [RCF:PROTECTED]
@router.get("", response_model=list[OrderResponse])
# [RCF:PROTECTED]
async def list_orders(
    status: str | None = None,
    assigned_agent_id: int | None = None,
    mine: bool = Query(False, description="Only orders assigned to an agent (assigned_agent_id set)"),
    source: str | None = None,
    campaign: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Order).options(selectinload(Order.items)).where(Order.user_id == user.id)
    if status:
        q = q.where(Order.status == status)
    if assigned_agent_id is not None:
        q = q.where(Order.assigned_agent_id == assigned_agent_id)
    elif mine:
        q = q.where(Order.assigned_agent_id.is_not(None))
    if source:
        q = q.where(Order.source == source)
    if campaign:
        q = q.where(Order.campaign == campaign)
    result = await db.execute(q.order_by(Order.created_at.desc()))
    return result.scalars().all()


# [RCF:PROTECTED]
@router.post("", response_model=OrderResponse, status_code=201)
# [RCF:PROTECTED]
async def create_order(body: OrderCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Contact must belong to this user.
    res = await db.execute(select(Contact).where(Contact.id == body.contact_id, Contact.user_id == user.id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contact not found")

    order = Order(
        user_id=user.id,
        contact_id=body.contact_id,
        deal_id=body.deal_id,
        currency=body.currency,
        assigned_agent_id=body.assigned_agent_id,
        source=body.source,
        campaign=body.campaign,
        notes=body.notes,
        status="pending",
        total=0.0,
    )
    for spec in body.items:
        order.items.append(await _build_item(db, user.id, spec))
    recompute_order_total(order)
    db.add(order)
    await db.commit()
    order = await _get_order(db, order.id, user.id)

    _fire_webhook(user.id, "order_created", {
        "order_id": order.id,
        "contact_id": order.contact_id,
        "total": order.total,
        "status": order.status,
    })
    return order


# ── single order CRUD ─────────────────────────────────────────────────────────
# [RCF:PROTECTED]
@router.get("/{order_id}", response_model=OrderResponse)
# [RCF:PROTECTED]
async def get_order(order_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _get_order(db, order_id, user.id)


# [RCF:PROTECTED]
@router.put("/{order_id}", response_model=OrderResponse)
# [RCF:PROTECTED]
async def update_order(order_id: int, body: OrderUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    order = await _get_order(db, order_id, user.id)
    if body.deal_id is not None:
        deal_res = await db.execute(select(Deal).where(Deal.id == body.deal_id, Deal.user_id == user.id))
        if not deal_res.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Deal not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(order, key, value)
    await db.commit()
    return await _get_order(db, order_id, user.id)


# [RCF:PROTECTED]
@router.delete("/{order_id}", status_code=204)
# [RCF:PROTECTED]
async def delete_order(order_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    order = await _get_order(db, order_id, user.id)
    await db.delete(order)
    await db.commit()


# ── status transitions ─────────────────────────────────────────────────────────
# [RCF:PROTECTED]
@router.put("/{order_id}/status", response_model=OrderResponse)
# [RCF:PROTECTED]
async def update_order_status(
    order_id: int,
    status: str = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if status not in ORDER_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {ORDER_STATUSES}")
    order = await _get_order(db, order_id, user.id)
    old_status = order.status
    if status == old_status:
        return order
    if not can_transition(old_status, status):
        allowed = ALLOWED_TRANSITIONS.get(old_status, [])
        raise HTTPException(
            status_code=400,
            detail=f"Cannot move order from '{old_status}' to '{status}'. Allowed: {allowed or 'none (terminal)'}",
        )
    order.status = status
    await log_order_status_change(db, user.id, order, old_status, status, agent_id=None)
    await db.commit()
    order = await _get_order(db, order_id, user.id)

    _fire_webhook(user.id, "order_status_changed", {
        "order_id": order.id,
        "old_status": old_status,
        "new_status": status,
    })
    return order


# ── history ──────────────────────────────────────────────────────────────────
# [RCF:PROTECTED]
@router.get("/{order_id}/history")
# [RCF:PROTECTED]
async def order_history(order_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _get_order(db, order_id, user.id)  # 404 if not owned
    result = await db.execute(
        select(Activity)
        .where(Activity.user_id == user.id, Activity.type == "order_status_changed")
        .order_by(Activity.created_at.desc())
    )
    activities = result.scalars().all()
    # order_id lives in metadata_json (Activity model is RCF-PROTECTED — no column).
    history = [
        {
            "id": a.id,
            "old_status": (a.metadata_json or {}).get("old_status"),
            "new_status": (a.metadata_json or {}).get("new_status"),
            "agent_id": a.agent_id,
            "created_at": a.created_at,
        }
        for a in activities
        if (a.metadata_json or {}).get("order_id") == order_id
    ]
    return history


# ── line items ─────────────────────────────────────────────────────────────────
# [RCF:PROTECTED]
@router.post("/{order_id}/items", response_model=OrderResponse, status_code=201)
# [RCF:PROTECTED]
async def add_order_item(order_id: int, body: OrderItemCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    order = await _get_order(db, order_id, user.id)
    order.items.append(await _build_item(db, user.id, body))
    recompute_order_total(order)
    await db.commit()
    return await _get_order(db, order_id, user.id)


# [RCF:PROTECTED]
@router.put("/{order_id}/items/{item_id}", response_model=OrderResponse)
# [RCF:PROTECTED]
async def update_order_item(
    order_id: int,
    item_id: int,
    body: OrderItemCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await _get_order(db, order_id, user.id)
    item = next((i for i in order.items if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Order item not found")
    rebuilt = await _build_item(db, user.id, body)
    item.product_id = rebuilt.product_id
    item.product_name = rebuilt.product_name
    item.quantity = rebuilt.quantity
    item.unit_price = rebuilt.unit_price
    recompute_order_total(order)
    await db.commit()
    return await _get_order(db, order_id, user.id)


# [RCF:PROTECTED]
@router.delete("/{order_id}/items/{item_id}", response_model=OrderResponse)
# [RCF:PROTECTED]
async def delete_order_item(order_id: int, item_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    order = await _get_order(db, order_id, user.id)
    item = next((i for i in order.items if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Order item not found")
    order.items.remove(item)
    recompute_order_total(order)
    await db.commit()
    return await _get_order(db, order_id, user.id)
