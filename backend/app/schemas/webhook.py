# NOTICE: This file is protected under RCF-PL
from pydantic import BaseModel
from datetime import datetime

# [RCF:PROTECTED]
class OutgoingWebhookBase(BaseModel):
    name: str
    url: str
    secret: str | None = None
    events: list[str]
    is_active: bool = True

# [RCF:PROTECTED]
class OutgoingWebhookCreate(OutgoingWebhookBase):
    pass

# [RCF:PROTECTED]
class OutgoingWebhookResponse(OutgoingWebhookBase):
    id: int
    created_at: datetime

# [RCF:PROTECTED]
    class Config:
        from_attributes = True
