# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""Pydantic schemas for the file workspace (spaces / folders / files)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Spaces ──────────────────────────────────────────────────────────────────


# [RCF:PROTECTED]
class SpaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


# [RCF:PROTECTED]
class SpaceUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


# [RCF:PROTECTED]
class SpaceOut(BaseModel):
    id: int
    name: str
    created_by_user_id: int
    my_role: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Members ─────────────────────────────────────────────────────────────────


# [RCF:PROTECTED]
class MemberAdd(BaseModel):
    """Add a member by user id (preferred) or email lookup."""

    user_id: Optional[int] = None
    email: Optional[str] = None
    role: str = Field("viewer", pattern="^(owner|editor|viewer)$")


# [RCF:PROTECTED]
class MemberUpdate(BaseModel):
    role: str = Field(..., pattern="^(owner|editor|viewer)$")


# [RCF:PROTECTED]
class MemberOut(BaseModel):
    user_id: int
    email: str
    name: Optional[str] = None
    role: str

    model_config = {"from_attributes": True}


# ── Folders ─────────────────────────────────────────────────────────────────


# [RCF:PROTECTED]
class FolderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    parent_id: Optional[int] = None


# [RCF:PROTECTED]
class FolderUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    parent_id: Optional[int] = None


# [RCF:PROTECTED]
class FolderOut(BaseModel):
    id: int
    space_id: int
    parent_id: Optional[int] = None
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Files ───────────────────────────────────────────────────────────────────


# [RCF:PROTECTED]
class FileRename(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)


# [RCF:PROTECTED]
class FileMove(BaseModel):
    folder_id: Optional[int] = None


# [RCF:PROTECTED]
class FileRestore(BaseModel):
    version_no: int


# [RCF:PROTECTED]
class FileOut(BaseModel):
    id: int
    space_id: int
    folder_id: Optional[int] = None
    name: str
    mime_type: Optional[str] = None
    byte_size: int
    current_version_no: int
    created_by_user_id: int
    deleted_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# [RCF:PROTECTED]
class VersionOut(BaseModel):
    id: int
    file_id: int
    version_no: int
    byte_size: int
    uploader_user_id: int
    author_type: str
    agent_run_id: Optional[int] = None
    comment: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# [RCF:PROTECTED]
class EventOut(BaseModel):
    id: int
    file_id: int
    event_type: str
    actor_type: str
    actor_user_id: Optional[int] = None
    # Display name resolved from the actor's user row (None for system).
    actor_name: Optional[str] = None
    payload: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
