from pydantic import BaseModel


class VMCreate(BaseModel):
    name: str
    host: str
    port: int = 22
    username: str = "root"
    ssh_key: str | None = None
    password: str | None = None


class VMResponse(BaseModel):
    id: int
    name: str
    host: str
    port: int
    username: str
    status: str

    model_config = {"from_attributes": True}


class LLMProviderCreate(BaseModel):
    name: str
    type: str  # nvidia_nim, openai, anthropic, ollama, custom
    api_key: str | None = None
    base_url: str


class LLMProviderResponse(BaseModel):
    id: int
    name: str
    type: str
    base_url: str
    status: str

    model_config = {"from_attributes": True}


class MongoCreate(BaseModel):
    name: str
    connection_string: str
    db_name: str


class MongoResponse(BaseModel):
    id: int
    name: str
    db_name: str
    status: str

    model_config = {"from_attributes": True}


class BentoMLCreate(BaseModel):
    name: str
    endpoint_url: str
    api_key: str | None = None


class BentoMLResponse(BaseModel):
    id: int
    name: str
    endpoint_url: str
    status: str

    model_config = {"from_attributes": True}

class BentoMLDeployRequest(BaseModel):
    service_name: str = "service:latest"
    port: int = 3000
