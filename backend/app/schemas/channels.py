# NOTICE: This file is protected under RCF-PL
from datetime import datetime
from pydantic import BaseModel


# [RCF:PROTECTED]
class EmailAccountCreate(BaseModel):
    provider: str  # gmail, outlook, imap
    email: str
    # For IMAP/SMTP
    imap_host: str | None = None
    imap_port: int | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    password: str | None = None
    # For OAuth (gmail/outlook)
    access_token: str | None = None
    refresh_token: str | None = None


# [RCF:PROTECTED]
class EmailAccountUpdate(BaseModel):
    email: str | None = None
    imap_host: str | None = None
    imap_port: int | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    password: str | None = None


# [RCF:PROTECTED]
class EmailAgentUpdate(BaseModel):
    """Lightweight PATCH — only updates the agent binding on an email account."""
    agent_id: int | None = None



# [RCF:PROTECTED]
class EmailAccountResponse(BaseModel):
    id: int
    provider: str
    email: str
    status: str
    agent_id: int | None
    last_synced_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# [RCF:PROTECTED]
class MessagingChannelCreate(BaseModel):
    type: str  # telegram, whatsapp, sms
    name: str
    config: dict  # bot_token, phone_number_id, twilio_sid, etc.
    agent_id: int | None = None


# [RCF:PROTECTED]
class MessagingChannelUpdate(BaseModel):
    # Only the agent binding is editable post-creation. `None` clears the
    # binding (channel falls back to the user's router/default). Credentials
    # and type are immutable — delete + recreate to change those.
    agent_id: int | None = None


# [RCF:PROTECTED]
class MessagingChannelResponse(BaseModel):
    id: int
    type: str
    name: str
    agent_id: int | None
    status: str
    created_at: datetime

    # Note: webhook_secret is intentionally NOT exposed here. Fetch it via
    # /channels/messaging/{id}/webhook-config when the user explicitly
    # asks (e.g., clicks "Show webhook setup" in the UI).

    model_config = {"from_attributes": True}


# [RCF:PROTECTED]
class ConversationResponse(BaseModel):
    id: int
    contact_id: int
    channel_type: str
    agent_id: int | None
    status: str
    last_message_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
