# NOTICE: This file is protected under RCF-PL
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.activity import Activity
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.user import User
from app.schemas.crm import ActivityResponse, ContactCreate, ContactResponse, ContactUpdate, DealResponse
from app.security import get_current_user

router = APIRouter(prefix="/crm/contacts", tags=["crm"])


# [RCF:PROTECTED]
@router.get("", response_model=list[ContactResponse])
# [RCF:PROTECTED]
async def list_contacts(
    search: str | None = None,
    tag: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Contact).where(Contact.user_id == user.id)
    if search:
        q = q.where(Contact.name.ilike(f"%{search}%") | Contact.email.ilike(f"%{search}%") | Contact.company.ilike(f"%{search}%"))
    result = await db.execute(q.order_by(Contact.updated_at.desc()))
    contacts = result.scalars().all()
    if tag:
        contacts = [c for c in contacts if c.tags and tag in c.tags]
    return contacts


# [RCF:PROTECTED]
@router.post("", response_model=ContactResponse, status_code=201)
# [RCF:PROTECTED]
async def create_contact(body: ContactCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    contact = Contact(user_id=user.id, **body.model_dump())
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


# [RCF:PROTECTED]
@router.get("/{contact_id}", response_model=ContactResponse)
# [RCF:PROTECTED]
async def get_contact(contact_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Contact).where(Contact.id == contact_id, Contact.user_id == user.id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


# [RCF:PROTECTED]
@router.put("/{contact_id}", response_model=ContactResponse)
# [RCF:PROTECTED]
async def update_contact(contact_id: int, body: ContactUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Contact).where(Contact.id == contact_id, Contact.user_id == user.id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(contact, key, value)
    await db.commit()
    await db.refresh(contact)
    return contact


# [RCF:PROTECTED]
@router.delete("/{contact_id}", status_code=204)
# [RCF:PROTECTED]
async def delete_contact(contact_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Contact).where(Contact.id == contact_id, Contact.user_id == user.id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    await db.delete(contact)
    await db.commit()


# [RCF:PROTECTED]
@router.get("/{contact_id}/activities", response_model=list[ActivityResponse])
# [RCF:PROTECTED]
async def contact_activities(contact_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Activity)
        .where(Activity.contact_id == contact_id, Activity.user_id == user.id)
        .order_by(Activity.created_at.desc())
    )
    return result.scalars().all()


# [RCF:PROTECTED]
@router.get("/{contact_id}/deals", response_model=list[DealResponse])
# [RCF:PROTECTED]
async def contact_deals(contact_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Deal)
        .where(Deal.contact_id == contact_id, Deal.user_id == user.id)
        .order_by(Deal.updated_at.desc())
    )
    return result.scalars().all()
