# NOTICE: This file is protected under RCF-PL
from typing import Literal

from pydantic import BaseModel


# [RCF:PROTECTED]
class RouterConfigCreate(BaseModel):
    name: str
    type: str  # keyword, llm_classifier, hybrid
    config: dict
    is_active: bool = False


# [RCF:PROTECTED]
class RouterConfigUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    config: dict | None = None
    is_active: bool | None = None


# [RCF:PROTECTED]
class RouterConfigResponse(BaseModel):
    id: int
    name: str
    type: str
    config: dict
    is_active: bool

    model_config = {"from_attributes": True}


# [RCF:PROTECTED]
class ChatRequest(BaseModel):
    message: str = ""  # may be empty when speaking — transcript comes from audio
    agent_id: int | None = None
    session_id: int | None = None  # если None — создаётся новая сессия
    attachments: list[dict] | None = None
    voice_reply: bool = False  # if True, the agent's reply is also synthesized to audio
    stream: bool = False



# [RCF:PROTECTED]
class ChatResponse(BaseModel):
    response: str
    agent_name: str
    model: str
    session_id: int
    message_id: int | None = None  # id of the persisted assistant reply (for feedback)
    attachments: list[dict] | None = None


# [RCF:PROTECTED]
class FeedbackRequest(BaseModel):
    value: Literal["thumbs_up", "thumbs_down"]


# [RCF:PROTECTED]
class FeedbackResponse(BaseModel):
    message_id: int
    value: str


# [RCF:PROTECTED]
class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    model: str | None
    attachments: list[dict] | None = None
    created_at: str
    feedback: str | None = None  # this user's reaction: thumbs_up | thumbs_down | None

    model_config = {"from_attributes": True}


# [RCF:PROTECTED]
class ChatSessionResponse(BaseModel):
    id: int
    agent_id: int
    title: str
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
