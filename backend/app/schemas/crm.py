from datetime import datetime
from pydantic import BaseModel


class ContactCreate(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    tags: list[str] | None = None
    source: str | None = None
    notes: str | None = None


class ContactUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    tags: list[str] | None = None
    notes: str | None = None


class ContactResponse(BaseModel):
    id: int
    name: str
    email: str | None
    phone: str | None
    company: str | None
    tags: list | None
    source: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DealCreate(BaseModel):
    contact_id: int
    title: str
    stage: str = "lead"
    amount: float | None = None
    currency: str = "USD"
    probability: int = 0
    assigned_agent_id: int | None = None
    notes: str | None = None


class DealUpdate(BaseModel):
    title: str | None = None
    stage: str | None = None
    amount: float | None = None
    currency: str | None = None
    probability: int | None = None
    assigned_agent_id: int | None = None
    notes: str | None = None


class DealResponse(BaseModel):
    id: int
    contact_id: int
    title: str
    stage: str
    amount: float | None
    currency: str
    probability: int
    assigned_agent_id: int | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ActivityCreate(BaseModel):
    contact_id: int
    deal_id: int | None = None
    type: str  # email_in, email_out, message_in, message_out, note, call
    channel: str | None = None
    subject: str | None = None
    content: str | None = None


class ActivityResponse(BaseModel):
    id: int
    contact_id: int
    deal_id: int | None
    type: str
    channel: str | None
    subject: str | None
    content: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
