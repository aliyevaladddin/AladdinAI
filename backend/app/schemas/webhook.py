# NOTICE: This file is protected under RCF-PL
from pydantic import BaseModel, ConfigDict
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
class OutgoingWebhookUpdate(BaseModel):
    """Partial update. `secret` follows three-state semantics: omitted → keep the
    current secret, empty string → remove signing (deliver unsigned), any other
    value → rotate to a new secret."""
    name: str | None = None
    url: str | None = None
    secret: str | None = None
    events: list[str] | None = None
    is_active: bool | None = None

# [RCF:PROTECTED]
class OutgoingWebhookResponse(OutgoingWebhookBase):
    id: int
    created_at: datetime

# [RCF:PROTECTED]
    model_config = ConfigDict(from_attributes=True)
