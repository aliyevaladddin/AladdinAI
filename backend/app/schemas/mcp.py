# NOTICE: This file is protected under RCF-PL
from datetime import datetime

from pydantic import BaseModel, Field


class McpServerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    url: str = Field(min_length=1, max_length=500)
    headers: dict[str, str] | None = None
    timeout_seconds: int = Field(default=30, ge=5, le=300)


class McpServerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    url: str | None = Field(default=None, min_length=1, max_length=500)
    headers: dict[str, str] | None = None
    enabled: bool | None = None
    timeout_seconds: int | None = Field(default=None, ge=5, le=300)


class CatalogEntry(BaseModel):
    name: str
    url: str
    category: str
    description: str
    headers_hint: dict[str, str] = {}


class McpToolInfo(BaseModel):
    name: str
    description: str = ""
    inputSchema: dict = {}


class McpServerResponse(BaseModel):
    id: int
    name: str
    url: str
    enabled: bool
    timeout_seconds: int
    # Header NAMES only — values never leave the backend.
    header_names: list[str] = []
    tools: list[McpToolInfo] = []
    last_checked_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class McpTestResult(BaseModel):
    status: str  # "success" | "error"
    tools: list[str] = []
    message: str | None = None
