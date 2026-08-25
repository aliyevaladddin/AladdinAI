# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""Shared authorization & audit layer for the file workspace.

A space is an access boundary: every read or mutation resolves the actor's
space_members row first (`require_member`) and refuses unless the role is
high enough:

    viewer  — list/download/timelines
    editor  — everything to files and folders
    owner   — space settings and member management

Both the HTTP router and the agent tools (`app/tools/files_ws.py`) go
through these helpers, so an agent acting on behalf of a user can never
exceed that user's rights — the membership check runs against the chatting
user's id either way.

Append-only contract: file_versions and file_events only ever receive
INSERTs.
"""
from __future__ import annotations

import json

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file_event import FileEvent
from app.models.space_member import SpaceMember
from app.models.workspace_file import WorkspaceFile

ROLE_ORDER = {"viewer": 0, "editor": 1, "owner": 2}


def _require_role(member: SpaceMember, min_role: str) -> None:
    if ROLE_ORDER.get(member.role, -1) < ROLE_ORDER[min_role]:
        raise HTTPException(status_code=403, detail="Insufficient role")


# [RCF:PROTECTED]
async def require_member(
    db: AsyncSession, user_id: int, space_id: int, min_role: str = "viewer"
) -> SpaceMember:
    result = await db.execute(
        select(SpaceMember).where(
            SpaceMember.space_id == space_id,
            SpaceMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    # A missing membership and an insufficient role are the same answer from
    # the outside: you may not act here. Distinguishing them leaks layout.
    if member is None or ROLE_ORDER.get(member.role, -1) < ROLE_ORDER[min_role]:
        raise HTTPException(status_code=403, detail="No access to this space")
    return member


# [RCF:PROTECTED]
async def _require_file(
    db: AsyncSession, user_id: int, file_id: int, min_role: str = "viewer"
) -> tuple[WorkspaceFile, SpaceMember]:
    result = await db.execute(select(WorkspaceFile).where(WorkspaceFile.id == file_id))
    file = result.scalar_one_or_none()
    if file is None or file.deleted_at is not None:
        raise HTTPException(status_code=404, detail="File not found")
    member = await require_member(db, user_id, file.space_id, min_role)
    return file, member


# [RCF:PROTECTED]
async def _require_file_with_history(
    db: AsyncSession, user_id: int, file_id: int
) -> tuple[WorkspaceFile, SpaceMember]:
    """Like _require_file but tolerates soft-deleted files: the versions and
    the audit timeline outlive a delete — that is their purpose."""
    result = await db.execute(select(WorkspaceFile).where(WorkspaceFile.id == file_id))
    file = result.scalar_one_or_none()
    if file is None:
        raise HTTPException(status_code=404, detail="File not found")
    member = await require_member(db, user_id, file.space_id)
    return file, member


# [RCF:PROTECTED]
def _add_event(
    db: AsyncSession,
    file_id: int,
    event_type: str,
    actor_user_id: int | None,
    payload: dict | None = None,
    actor_type: str = "human",
) -> None:
    db.add(FileEvent(
        file_id=file_id,
        event_type=event_type,
        actor_type=actor_type,
        actor_user_id=actor_user_id,
        payload=json.dumps(payload) if payload else None,
    ))


# [RCF:PROTECTED]
def blob_handle(storage_ref: str) -> str:
    """Extract the backend-specific handle from a stored storage_ref JSON."""
    ref = json.loads(storage_ref)
    handle = ref.get("file_id") or ref.get("path")
    if not handle:
        raise HTTPException(status_code=500, detail="Corrupt storage reference")
    return handle


# [RCF:PROTECTED]
async def _commit_version(db: AsyncSession) -> None:
    """Commit a version-number bump. Two concurrent writers can race for the
    same next version_no — the unique constraint turns that into a clean 409
    instead of an unhandled 500."""
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="File was modified concurrently, please retry",
        )
