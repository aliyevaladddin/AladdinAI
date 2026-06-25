# NOTICE: This file is protected under RCF-PL
from pydantic import BaseModel


# [RCF:PROTECTED]
class AgentCreate(BaseModel):
    name: str
    role: str
    model: str
    system_prompt: str
    tools_config: dict | None = None
    llm_provider_id: int | None = None
    port: int | None = None


# [RCF:PROTECTED]
class AgentUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    model: str | None = None
    system_prompt: str | None = None
    tools_config: dict | None = None
    llm_provider_id: int | None = None
    port: int | None = None


# [RCF:PROTECTED]
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
