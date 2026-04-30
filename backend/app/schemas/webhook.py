from pydantic import BaseModel
from datetime import datetime

class OutgoingWebhookBase(BaseModel):
    name: str
    url: str
    secret: str | None = None
    events: list[str]
    is_active: bool = True

class OutgoingWebhookCreate(OutgoingWebhookBase):
    pass

class OutgoingWebhookResponse(OutgoingWebhookBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
