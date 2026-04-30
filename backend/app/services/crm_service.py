from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.contact import Contact


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
