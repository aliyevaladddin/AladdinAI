# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""Pydantic schemas for the terminal-provider marketplace & runtime."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MarketplaceEntry(BaseModel):
    """One row in the dashboard marketplace — read straight from a YAML manifest."""

    type: str
    name: str
    description: Optional[str] = None
    image: str
    internal_port: int
    requires_ssh_proxy: bool = False


class ProviderInstall(BaseModel):
    """Install request — picks an entry from the marketplace by `type`."""

    type: str = Field(..., description="Manifest type, e.g. 'ttyd'")
    name: Optional[str] = Field(None, description="Display name; defaults to manifest name")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ProviderResponse(BaseModel):
    id: int
    name: str
    type: str
    source: str
    image: str
    internal_port: int
    host_port: Optional[int] = None
    requires_ssh_proxy: bool
    is_active: bool
    status: str
    container_id: Optional[str] = None
    last_health_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionRequest(BaseModel):
    """`POST /terminal/session` — what the drawer sends.

    `vm_id` is reserved for adapters with `requires_ssh_proxy=true`; the MVP
    ttyd adapter ignores it.
    """
    vm_id: Optional[int] = None


class SessionResponse(BaseModel):
    url: str
    expires_at: datetime
    provider_type: str
    provider_session_id: Optional[str] = None
