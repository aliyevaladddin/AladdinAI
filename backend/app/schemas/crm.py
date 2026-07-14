# NOTICE: This file is protected under RCF-PL
from datetime import datetime
from pydantic import BaseModel


# [RCF:PROTECTED]
class ContactCreate(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    tags: list[str] | None = None
    source: str | None = None
    notes: str | None = None


# [RCF:PROTECTED]
class ContactUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    tags: list[str] | None = None
    notes: str | None = None


# [RCF:PROTECTED]
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


# [RCF:PROTECTED]
class DealCreate(BaseModel):
    contact_id: int
    title: str
    stage: str = "lead"
    amount: float | None = None
    currency: str = "USD"
    probability: int = 0
    assigned_agent_id: int | None = None
    notes: str | None = None


# [RCF:PROTECTED]
class DealUpdate(BaseModel):
    title: str | None = None
    stage: str | None = None
    amount: float | None = None
    currency: str | None = None
    probability: int | None = None
    assigned_agent_id: int | None = None
    notes: str | None = None


# [RCF:PROTECTED]
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


# ── Products ─────────────────────────────────────────────────────────────────
# [RCF:PROTECTED]
class ProductCreate(BaseModel):
    sku: str
    name: str
    description: str | None = None
    price: float = 0.0
    currency: str = "USD"
    active: bool = True


# [RCF:PROTECTED]
class ProductUpdate(BaseModel):
    sku: str | None = None
    name: str | None = None
    description: str | None = None
    price: float | None = None
    currency: str | None = None
    active: bool | None = None


# [RCF:PROTECTED]
class ProductResponse(BaseModel):
    id: int
    sku: str
    name: str
    description: str | None
    price: float
    currency: str
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Orders ───────────────────────────────────────────────────────────────────
# [RCF:PROTECTED]
class OrderItemCreate(BaseModel):
    product_id: int | None = None
    product_name: str | None = None  # required if product_id is omitted
    quantity: int = 1
    unit_price: float | None = None  # overrides the product's catalog price when set


# [RCF:PROTECTED]
class OrderItemResponse(BaseModel):
    id: int
    product_id: int | None
    product_name: str
    quantity: int
    unit_price: float
    line_total: float

    model_config = {"from_attributes": True}


# [RCF:PROTECTED]
class OrderCreate(BaseModel):
    contact_id: int
    deal_id: int | None = None
    currency: str = "USD"
    assigned_agent_id: int | None = None
    source: str | None = None
    campaign: str | None = None
    notes: str | None = None
    items: list[OrderItemCreate] = []


# [RCF:PROTECTED]
class OrderUpdate(BaseModel):
    # status and total are NOT editable here — status moves via /status, total is derived.
    deal_id: int | None = None
    currency: str | None = None
    assigned_agent_id: int | None = None
    source: str | None = None
    campaign: str | None = None
    notes: str | None = None


# [RCF:PROTECTED]
class OrderResponse(BaseModel):
    id: int
    contact_id: int
    deal_id: int | None
    status: str
    total: float
    currency: str
    assigned_agent_id: int | None
    source: str | None
    campaign: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse] = []

    model_config = {"from_attributes": True}


# [RCF:PROTECTED]
class OrderMetricsResponse(BaseModel):
    realized_revenue: float       # Σ total of delivered orders
    booked_revenue: float         # Σ total of non-cancelled orders
    order_count: int
    count_by_status: dict[str, int]
    revenue_by_status: dict[str, float]
    pipeline_value: float         # Σ Deal.amount for open stages
    funnel: dict[str, int]        # deal count by stage
    win_rate: float               # won / (won + lost)
    revenue_by_source: dict[str, float]
    revenue_by_campaign: dict[str, float]


# [RCF:PROTECTED]
class ActivityCreate(BaseModel):
    contact_id: int | None = None
    deal_id: int | None = None
    type: str  # email_in, email_out, message_in, message_out, note, call
    channel: str | None = None
    subject: str | None = None
    content: str | None = None
    metadata_json: dict | None = None


# [RCF:PROTECTED]
class ActivityResponse(BaseModel):
    id: int
    contact_id: int | None
    deal_id: int | None
    type: str
    channel: str | None
    subject: str | None
    content: str | None
    metadata_json: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
