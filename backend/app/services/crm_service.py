# NOTICE: This file is protected under RCF-PL
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.contact import Contact
from app.models.order import Order

# Order delivery lifecycle. cancelled/delivered are terminal — no edge leaves them.
ORDER_STATUSES = ["pending", "processing", "shipped", "delivered", "cancelled"]
ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["processing", "cancelled"],
    "processing": ["shipped", "cancelled"],
    "shipped": ["delivered", "cancelled"],
    "delivered": [],
    "cancelled": [],
}


# [RCF:PROTECTED]
async def find_or_create_contact(
    db: AsyncSession,
    user_id: int,
    identifier: str,
    name: str = "",
    source: str = "auto",
    is_phone: bool = False,
) -> Contact:
    """Find existing contact by email/phone or create new one."""
    if is_phone:
        result = await db.execute(
            select(Contact).where(Contact.user_id == user_id, Contact.phone == identifier)
        )
    else:
        result = await db.execute(
            select(Contact).where(Contact.user_id == user_id, Contact.email == identifier)
        )
    contact = result.scalar_one_or_none()

    if not contact:
        contact = Contact(
            user_id=user_id,
            name=name or identifier,
            email=None if is_phone else identifier,
            phone=identifier if is_phone else None,
            source=source,
        )
        db.add(contact)
        await db.flush()

    return contact


# [RCF:PROTECTED]
async def log_activity(
    db: AsyncSession,
    user_id: int,
    contact_id: int,
    activity_type: str,
    channel: str,
    content: str,
    subject: str | None = None,
    deal_id: int | None = None,
) -> Activity:
    """Log an activity in the CRM timeline."""
    activity = Activity(
        user_id=user_id,
        contact_id=contact_id,
        deal_id=deal_id,
        type=activity_type,
        channel=channel,
        subject=subject,
        content=content[:2000] if content else None,
    )
    db.add(activity)
    await db.flush()
    return activity


# ── Order helpers (shared by the router and agent tools) ─────────────────────
# [RCF:PROTECTED]
def recompute_order_total(order: Order) -> float:
    """Recompute each line's line_total and the order's denormalised total from
    its loaded items. Caller is responsible for flushing/committing."""
    total = 0.0
    for item in order.items:
        item.line_total = round((item.unit_price or 0.0) * (item.quantity or 0), 2)
        total += item.line_total
    order.total = round(total, 2)
    return order.total


# [RCF:PROTECTED]
def can_transition(current: str, target: str) -> bool:
    """True if `current` → `target` is a legal move in the status graph."""
    return target in ALLOWED_TRANSITIONS.get(current, [])


# [RCF:PROTECTED]
async def log_order_status_change(
    db: AsyncSession,
    user_id: int,
    order: Order,
    old_status: str,
    new_status: str,
    agent_id: int | None = None,
) -> Activity:
    """Append an order status change to the CRM timeline.

    The order linkage lives in metadata_json (not a column) so the RCF-PROTECTED
    Activity model stays untouched; /history filters on metadata_json.order_id.
    """
    activity = Activity(
        user_id=user_id,
        contact_id=order.contact_id,
        deal_id=order.deal_id,
        agent_id=agent_id,
        type="order_status_changed",
        channel="crm",
        subject=f"Order #{order.id}: {old_status} → {new_status}",
        content=None,
        metadata_json={
            "order_id": order.id,
            "old_status": old_status,
            "new_status": new_status,
        },
    )
    db.add(activity)
    await db.flush()
    return activity
