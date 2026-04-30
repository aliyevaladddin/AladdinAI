from pydantic import BaseModel


class RouterConfigCreate(BaseModel):
    name: str
    type: str  # keyword, llm_classifier, hybrid
    config: dict
    is_active: bool = False


class RouterConfigUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    config: dict | None = None
    is_active: bool | None = None


class RouterConfigResponse(BaseModel):
    id: int
    name: str
    type: str
    config: dict
    is_active: bool

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    message: str
    agent_id: int | None = None
    session_id: int | None = None  # если None — создаётся новая сессия


class ChatResponse(BaseModel):
    response: str
    agent_name: str
    model: str
    session_id: int


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    model: str | None
    created_at: str

    model_config = {"from_attributes": True}


class ChatSessionResponse(BaseModel):
    id: int
    agent_id: int
    title: str
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
