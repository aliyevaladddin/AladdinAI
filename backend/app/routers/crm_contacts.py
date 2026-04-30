from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.activity import Activity
from app.models.contact import Contact
from app.models.user import User
from app.schemas.crm import ActivityResponse, ContactCreate, ContactResponse, ContactUpdate
from app.security import get_current_user

router = APIRouter(prefix="/crm/contacts", tags=["crm"])


@router.get("", response_model=list[ContactResponse])
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


@router.post("", response_model=ContactResponse, status_code=201)
async def create_contact(body: ContactCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    contact = Contact(user_id=user.id, **body.model_dump())
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(contact_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Contact).where(Contact.id == contact_id, Contact.user_id == user.id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.put("/{contact_id}", response_model=ContactResponse)
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


@router.delete("/{contact_id}", status_code=204)
async def delete_contact(contact_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Contact).where(Contact.id == contact_id, Contact.user_id == user.id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    await db.delete(contact)
    await db.commit()


@router.get("/{contact_id}/activities", response_model=list[ActivityResponse])
async def contact_activities(contact_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Activity)
        .where(Activity.contact_id == contact_id, Activity.user_id == user.id)
        .order_by(Activity.created_at.desc())
    )
    return result.scalars().all()
