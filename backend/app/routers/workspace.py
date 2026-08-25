# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""
File workspace router: spaces → folders → files → versions → events.

Authorization model (variant B): a space is an access boundary. Every
endpoint resolves the caller's space_members row first (`require_member`)
and 403s unless the role is high enough:

    viewer  — list/download/timelines
    editor  — everything to files and folders
    owner   — space settings and member management

Append-only contract: file_versions and file_events only ever receive
INSERTs. Restoring inserts a new version pointing at the old storage_ref;
deleting is soft (files.deleted_at).

Blob scope: media backends store bytes under the uploading user
(media_mongo verifies metadata.user_id on read), so downloads read through
the ORIGINAL uploader's user id stored on each version — authorization for
who may read stays here.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.file_event import FileEvent
from app.models.file_version import FileVersion
from app.models.folder import Folder
from app.models.space import Space
from app.models.space_member import SpaceMember
from app.models.user import User
from app.models.workspace_file import WorkspaceFile
from app.schemas.workspace import (
    EventOut,
    FileMove,
    FileOut,
    FileRename,
    FileRestore,
    FolderCreate,
    FolderOut,
    FolderUpdate,
    MemberAdd,
    MemberOut,
    MemberUpdate,
    SpaceCreate,
    SpaceOut,
    SpaceUpdate,
    VersionOut,
)
from app.security import get_current_user
from app.services import media_storage

log = logging.getLogger(__name__)

router = APIRouter(tags=["Workspace"])

ROLE_ORDER = {"viewer": 0, "editor": 1, "owner": 2}

# Keep in sync with media_mongo.MAX_FILE_SIZE (mongo raises ValueError past it;
# we pre-check so local backend enforces the same limit).
MAX_FILE_SIZE = 50 * 1024 * 1024


# ── helpers ─────────────────────────────────────────────────────────────────


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
) -> None:
    db.add(FileEvent(
        file_id=file_id,
        event_type=event_type,
        actor_type="human",
        actor_user_id=actor_user_id,
        payload=json.dumps(payload) if payload else None,
    ))


# [RCF:PROTECTED]
def _blob_handle(storage_ref: str) -> str:
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


# ── spaces ──────────────────────────────────────────────────────────────────


@router.post("/spaces", response_model=SpaceOut, status_code=201)
async def create_space(
    body: SpaceCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    space = Space(name=body.name, created_by_user_id=user.id)
    db.add(space)
    await db.flush()
    db.add(SpaceMember(space_id=space.id, user_id=user.id, role="owner"))
    await db.commit()
    await db.refresh(space)
    return SpaceOut(
        id=space.id, name=space.name,
        created_by_user_id=space.created_by_user_id,
        my_role="owner", created_at=space.created_at,
    )


@router.get("/spaces", response_model=list[SpaceOut])
async def list_spaces(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Space, SpaceMember.role)
        .join(SpaceMember, SpaceMember.space_id == Space.id)
        .where(SpaceMember.user_id == user.id)
        .order_by(Space.id)
    )
    return [
        SpaceOut(
            id=space.id, name=space.name,
            created_by_user_id=space.created_by_user_id,
            my_role=role, created_at=space.created_at,
        )
        for space, role in result.all()
    ]


@router.patch("/spaces/{space_id}", response_model=SpaceOut)
async def rename_space(
    space_id: int,
    body: SpaceUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    member = await require_member(db, user.id, space_id, "owner")
    space = await db.get(Space, space_id)
    if space is None:
        raise HTTPException(status_code=404, detail="Space not found")
    space.name = body.name
    await db.commit()
    await db.refresh(space)
    return SpaceOut(
        id=space.id, name=space.name,
        created_by_user_id=space.created_by_user_id,
        my_role=member.role, created_at=space.created_at,
    )


@router.delete("/spaces/{space_id}", status_code=204)
async def delete_space(
    space_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_member(db, user.id, space_id, "owner")
    space = await db.get(Space, space_id)
    if space is None:
        raise HTTPException(status_code=404, detail="Space not found")
    await db.delete(space)
    await db.commit()
    return Response(status_code=204)


# ── members ─────────────────────────────────────────────────────────────────


@router.post("/spaces/{space_id}/members", response_model=MemberOut, status_code=201)
async def add_member(
    space_id: int,
    body: MemberAdd,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_member(db, user.id, space_id, "owner")

    target: User | None = None
    if body.user_id is not None:
        target = await db.get(User, body.user_id)
    elif body.email:
        result = await db.execute(select(User).where(User.email == body.email))
        target = result.scalar_one_or_none()
    else:
        raise HTTPException(status_code=422, detail="user_id or email required")
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    existing = await db.execute(
        select(SpaceMember).where(
            SpaceMember.space_id == space_id, SpaceMember.user_id == target.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Already a member")

    member_row = SpaceMember(space_id=space_id, user_id=target.id, role=body.role)
    db.add(member_row)
    await db.commit()
    return MemberOut(
        user_id=target.id, email=target.email,
        name=getattr(target, "name", None), role=member_row.role,
    )


@router.get("/spaces/{space_id}/members", response_model=list[MemberOut])
async def list_members(
    space_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_member(db, user.id, space_id)
    result = await db.execute(
        select(User, SpaceMember.role)
        .join(SpaceMember, SpaceMember.user_id == User.id)
        .where(SpaceMember.space_id == space_id)
        .order_by(User.id)
    )
    return [
        MemberOut(user_id=u.id, email=u.email, name=getattr(u, "name", None), role=role)
        for u, role in result.all()
    ]


# [RCF:PROTECTED]
async def _guard_last_owner(db: AsyncSession, space_id: int, user_id: int) -> None:
    owners = await db.execute(
        select(SpaceMember).where(
            SpaceMember.space_id == space_id, SpaceMember.role == "owner",
        )
    )
    owner_rows = owners.scalars().all()
    if len(owner_rows) == 1 and owner_rows[0].user_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot remove the last owner")


@router.patch("/spaces/{space_id}/members/{user_id}", response_model=MemberOut)
async def update_member(
    space_id: int,
    user_id: int,
    body: MemberUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_member(db, user.id, space_id, "owner")
    result = await db.execute(
        select(SpaceMember).where(
            SpaceMember.space_id == space_id, SpaceMember.user_id == user_id,
        )
    )
    member_row = result.scalar_one_or_none()
    if member_row is None:
        raise HTTPException(status_code=404, detail="Not a member")
    if member_row.role == "owner" and body.role != "owner":
        await _guard_last_owner(db, space_id, user_id)
    member_row.role = body.role
    await db.commit()

    target = await db.get(User, user_id)
    return MemberOut(
        user_id=user_id, email=target.email if target else "",
        name=getattr(target, "name", None), role=member_row.role,
    )


@router.delete("/spaces/{space_id}/members/{user_id}", status_code=204)
async def remove_member(
    space_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_member(db, user.id, space_id, "owner")
    result = await db.execute(
        select(SpaceMember).where(
            SpaceMember.space_id == space_id, SpaceMember.user_id == user_id,
        )
    )
    member_row = result.scalar_one_or_none()
    if member_row is None:
        raise HTTPException(status_code=404, detail="Not a member")
    if member_row.role == "owner":
        await _guard_last_owner(db, space_id, user_id)
    await db.delete(member_row)
    await db.commit()
    return Response(status_code=204)


# ── folders ─────────────────────────────────────────────────────────────────


@router.post("/spaces/{space_id}/folders", response_model=FolderOut, status_code=201)
async def create_folder(
    space_id: int,
    body: FolderCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_member(db, user.id, space_id, "editor")
    if body.parent_id is not None:
        parent = await db.get(Folder, body.parent_id)
        if parent is None or parent.space_id != space_id:
            raise HTTPException(status_code=400, detail="Parent folder not in this space")
    folder = Folder(space_id=space_id, parent_id=body.parent_id, name=body.name)
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return folder


@router.get("/spaces/{space_id}/folders", response_model=list[FolderOut])
async def list_folders(
    space_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_member(db, user.id, space_id)
    result = await db.execute(
        select(Folder).where(Folder.space_id == space_id).order_by(Folder.name)
    )
    return result.scalars().all()


@router.patch("/folders/{folder_id}", response_model=FolderOut)
async def update_folder(
    folder_id: int,
    body: FolderUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    folder = await db.get(Folder, folder_id)
    if folder is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    await require_member(db, user.id, folder.space_id, "editor")

    new_parent = body.parent_id if body.parent_id is not None else folder.parent_id
    if body.parent_id is not None:
        parent = await db.get(Folder, body.parent_id)
        if parent is None or parent.space_id != folder.space_id:
            raise HTTPException(status_code=400, detail="Parent folder not in this space")
        # Walk up the target chain; landing inside ourselves would be a cycle.
        cursor: Folder | None = parent
        while cursor is not None:
            if cursor.id == folder.id:
                raise HTTPException(status_code=400, detail="Cannot move a folder into itself")
            cursor = await db.get(Folder, cursor.parent_id) if cursor.parent_id else None

    if body.name is not None:
        folder.name = body.name
    folder.parent_id = new_parent
    await db.commit()
    await db.refresh(folder)
    return folder


@router.delete("/folders/{folder_id}", status_code=204)
async def delete_folder(
    folder_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    folder = await db.get(Folder, folder_id)
    if folder is None:
        raise HTTPException(status_code=404, detail="Folder not found")
    await require_member(db, user.id, folder.space_id, "editor")
    # Files fall back to the space root via FK SET NULL; child folders are
    # re-rooted the same way.
    await db.delete(folder)
    await db.commit()
    return Response(status_code=204)


# ── files ───────────────────────────────────────────────────────────────────


@router.get("/spaces/{space_id}/files", response_model=list[FileOut])
async def list_files(
    space_id: int,
    folder_id: Optional[int] = None,
    root: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List files of a space. ?root=true → only files not in any folder;
    ?folder_id=N → that folder; without params → everything (search etc.)."""
    await require_member(db, user.id, space_id)
    query = select(WorkspaceFile).where(
        WorkspaceFile.space_id == space_id,
        WorkspaceFile.deleted_at.is_(None),
    )
    if root:
        query = query.where(WorkspaceFile.folder_id.is_(None))
    elif folder_id is not None:
        query = query.where(WorkspaceFile.folder_id == folder_id)
    result = await db.execute(query.order_by(WorkspaceFile.name))
    return result.scalars().all()


@router.post("/spaces/{space_id}/files/upload", response_model=FileOut, status_code=201)
async def upload_file(
    space_id: int,
    file: UploadFile = File(...),
    folder_id: Optional[int] = Form(None),
    comment: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    member = await require_member(db, user.id, space_id, "editor")
    if folder_id is not None:
        folder = await db.get(Folder, folder_id)
        if folder is None or folder.space_id != space_id:
            raise HTTPException(status_code=400, detail="Folder not in this space")

    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    ref = await media_storage.save_bytes(
        db, user.id, data, file.content_type, original_filename=file.filename,
    )

    ws_file = WorkspaceFile(
        space_id=space_id,
        folder_id=folder_id,
        name=file.filename or "untitled",
        mime_type=file.content_type,
        byte_size=len(data),
        current_version_no=0,
        created_by_user_id=user.id,
    )
    db.add(ws_file)
    await db.flush()

    version = FileVersion(
        file_id=ws_file.id,
        version_no=1,
        storage_ref=json.dumps(ref),
        byte_size=len(data),
        uploader_user_id=user.id,
        author_type="human",
        comment=comment,
    )
    db.add(version)
    await db.flush()

    ws_file.current_version_no = 1
    ws_file.source_version_id = version.id
    _add_event(db, ws_file.id, "created", member.user_id)
    _add_event(db, ws_file.id, "version_added", member.user_id,
               {"version_no": 1})
    await db.commit()
    await db.refresh(ws_file)
    return ws_file


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: int,
    version: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ws_file, member = await _require_file(db, user.id, file_id)

    wanted = version or ws_file.current_version_no
    result = await db.execute(
        select(FileVersion).where(
            FileVersion.file_id == file_id, FileVersion.version_no == wanted,
        )
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")

    data = await media_storage.get_bytes(
        db, version.uploader_user_id, _blob_handle(version.storage_ref),
    )
    if data is None:
        raise HTTPException(status_code=404, detail="Stored content unavailable")

    _add_event(db, ws_file.id, "downloaded", member.user_id,
               {"version_no": wanted})
    await db.commit()

    filename = ws_file.name.replace('"', "")
    return Response(
        content=data,
        media_type=ws_file.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/files/{file_id}/upload_version", response_model=VersionOut, status_code=201)
async def upload_new_version(
    file_id: int,
    file: UploadFile = File(...),
    comment: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload updated content as the next version of an existing file."""
    ws_file, member = await _require_file(db, user.id, file_id, "editor")

    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    ref = await media_storage.save_bytes(
        db, user.id, data, file.content_type, original_filename=ws_file.name,
    )

    new_no = ws_file.current_version_no + 1
    version = FileVersion(
        file_id=file_id,
        version_no=new_no,
        storage_ref=json.dumps(ref),
        byte_size=len(data),
        uploader_user_id=user.id,
        author_type="human",
        comment=comment,
    )
    db.add(version)

    ws_file.current_version_no = new_no
    ws_file.byte_size = len(data)
    _add_event(db, file_id, "version_added", member.user_id,
               {"version_no": new_no})
    await _commit_version(db)
    await db.refresh(version)
    return version


@router.patch("/files/{file_id}", response_model=FileOut)
async def rename_file(
    file_id: int,
    body: FileRename,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ws_file, member = await _require_file(db, user.id, file_id, "editor")
    payload = {"from": ws_file.name, "to": body.name}
    ws_file.name = body.name
    _add_event(db, file_id, "renamed", member.user_id, payload)
    await db.commit()
    await db.refresh(ws_file)
    return ws_file


@router.post("/files/{file_id}/restore", response_model=VersionOut)
async def restore_version(
    file_id: int,
    body: FileRestore,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ws_file, member = await _require_file(db, user.id, file_id, "editor")

    result = await db.execute(
        select(FileVersion).where(
            FileVersion.file_id == file_id,
            FileVersion.version_no == body.version_no,
        )
    )
    source = result.scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=404, detail="Version not found")

    new_no = ws_file.current_version_no + 1
    # Same blob as the source, NEW row — history stays append-only. The blob
    # keeps being read through the original uploader's scope.
    version = FileVersion(
        file_id=file_id,
        version_no=new_no,
        storage_ref=source.storage_ref,
        byte_size=source.byte_size,
        uploader_user_id=source.uploader_user_id,
        author_type="human",
        comment=f"restored v{source.version_no}",
    )
    db.add(version)
    ws_file.current_version_no = new_no
    ws_file.byte_size = source.byte_size
    _add_event(db, file_id, "restored", member.user_id,
               {"from_version": source.version_no, "new_version": new_no})
    await _commit_version(db)
    await db.refresh(version)
    return version


@router.patch("/files/{file_id}/move", response_model=FileOut)
async def move_file(
    file_id: int,
    body: FileMove,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ws_file, member = await _require_file(db, user.id, file_id, "editor")
    if body.folder_id is not None:
        folder = await db.get(Folder, body.folder_id)
        if folder is None or folder.space_id != ws_file.space_id:
            raise HTTPException(status_code=400, detail="Folder not in this space")

    payload = {"from": ws_file.folder_id, "to": body.folder_id}
    ws_file.folder_id = body.folder_id
    _add_event(db, file_id, "moved", member.user_id, payload)
    await db.commit()
    await db.refresh(ws_file)
    return ws_file


@router.delete("/files/{file_id}", status_code=204)
async def delete_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ws_file, member = await _require_file(db, user.id, file_id, "editor")
    ws_file.deleted_at = datetime.now(timezone.utc)
    _add_event(db, file_id, "deleted", member.user_id)
    await db.commit()
    return Response(status_code=204)


@router.get("/files/{file_id}/versions", response_model=list[VersionOut])
async def list_versions(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ws_file, _member = await _require_file_with_history(db, user.id, file_id)
    result = await db.execute(
        select(FileVersion)
        .where(FileVersion.file_id == file_id)
        .order_by(FileVersion.version_no.desc())
    )
    return result.scalars().all()


@router.get("/files/{file_id}/events", response_model=list[EventOut])
async def list_events(
    file_id: int,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ws_file, _member = await _require_file_with_history(db, user.id, file_id)
    result = await db.execute(
        select(FileEvent, User)
        .join(User, User.id == FileEvent.actor_user_id, isouter=True)
        .where(FileEvent.file_id == file_id)
        .order_by(FileEvent.created_at.desc(), FileEvent.id.desc())
        .limit(min(limit, 500))
    )
    return [
        EventOut(
            id=ev.id,
            file_id=ev.file_id,
            event_type=ev.event_type,
            actor_type=ev.actor_type,
            actor_user_id=ev.actor_user_id,
            actor_name=(getattr(u, "name", None) or u.email) if u else None,
            payload=ev.payload,
            created_at=ev.created_at,
        )
        for ev, u in result.all()
    ]
