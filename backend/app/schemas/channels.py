from datetime import datetime
from pydantic import BaseModel


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


class EmailAccountResponse(BaseModel):
    id: int
    provider: str
    email: str
    status: str
    last_synced_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MessagingChannelCreate(BaseModel):
    type: str  # telegram, whatsapp, sms
    name: str
    config: dict  # bot_token, phone_number_id, twilio_sid, etc.
    agent_id: int | None = None


class MessagingChannelResponse(BaseModel):
    id: int
    type: str
    name: str
    agent_id: int | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: int
    contact_id: int
    channel_type: str
    agent_id: int | None
    status: str
    last_message_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
