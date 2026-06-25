# NOTICE: This file is protected under RCF-PL
from pydantic import BaseModel


# [RCF:PROTECTED]
class VMCreate(BaseModel):
    name: str
    host: str
    port: int = 22
    username: str = "root"
    ssh_key: str | None = None
    password: str | None = None


# [RCF:PROTECTED]
class VMResponse(BaseModel):
    id: int
    name: str
    host: str
    port: int
    username: str
    status: str

    model_config = {"from_attributes": True}


# [RCF:PROTECTED]
class LLMProviderCreate(BaseModel):
    name: str
    type: str  # nvidia_nim, openai, anthropic, ollama, custom
    api_key: str | None = None
    base_url: str


# [RCF:PROTECTED]
class LLMProviderResponse(BaseModel):
    id: int
    name: str
    type: str
    base_url: str
    status: str

    model_config = {"from_attributes": True}


# [RCF:PROTECTED]
class MongoCreate(BaseModel):
    name: str
    connection_string: str | None = None
    db_name: str


# [RCF:PROTECTED]
class MongoResponse(BaseModel):
    id: int
    name: str
    db_name: str
    status: str

    model_config = {"from_attributes": True}


# [RCF:PROTECTED]
class BentoMLCreate(BaseModel):
    name: str
    endpoint_url: str
    api_key: str | None = None


# [RCF:PROTECTED]
class BentoMLResponse(BaseModel):
    id: int
    name: str
    endpoint_url: str
    status: str

    model_config = {"from_attributes": True}

# [RCF:PROTECTED]
class BentoMLDeployRequest(BaseModel):
    service_name: str = "service:latest"
    port: int = 3000
