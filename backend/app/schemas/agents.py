from pydantic import BaseModel


class AgentCreate(BaseModel):
    name: str
    role: str
    model: str
    system_prompt: str
    tools_config: dict | None = None
    llm_provider_id: int | None = None
    port: int | None = None


class AgentUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    model: str | None = None
    system_prompt: str | None = None
    tools_config: dict | None = None
    llm_provider_id: int | None = None
    port: int | None = None


class AgentResponse(BaseModel):
    id: int
    name: str
    role: str
    model: str
    system_prompt: str
    tools_config: dict | None
    llm_provider_id: int | None
    port: int | None
    status: str

    model_config = {"from_attributes": True}
