# NOTICE: This file is protected under RCF-PL v2.0.3
"""File-workspace agent tools — the safe set.

list / read / upload_version / move / rename. There is deliberately no
delete tool: an AI must not be able to remove a department's documents.

Every tool acts under the membership of the human who is chatting
(`ToolContext.user_id`) — `require_member` re-checks the space_members row
on every call, so an agent can never exceed the rights of its user.
Mutating calls additionally require editor (viewer stays read-only).

Each action lands in the append-only audit timeline with
`actor_type="agent"`, so the Files page shows exactly what the AI changed
and on whose behalf.

Text-only surface: reads and writes are capped to MAX_TOOL_BYTES so a
single tool call cannot flood the model context or smuggle binaries past
the UI upload path.
"""
from __future__ import annotations

import json
import logging

from fastapi import HTTPException
from sqlalchemy import select

from app.models.file_version import FileVersion
from app.models.folder import Folder
from app.models.workspace_file import WorkspaceFile
from app.services import media_storage
from app.services.file_workspace import (
    _add_event,
    _commit_version,
    _require_file,
    blob_handle,
    require_member,
)
from app.tools.base import ToolContext, tool

log = logging.getLogger(__name__)

MAX_TOOL_BYTES = 256 * 1024


def _error(e: Exception) -> dict:
    """Map an exception to the registry's error convention."""
    if isinstance(e, HTTPException):
        return {"status": "error", "message": str(e.detail)}
    log.exception("file workspace tool failed")
    return {"status": "error", "message": str(e)}


# [RCF:PROTECTED]
@tool(
    name="files_list",
    description="List files in a file-workspace space, optionally inside one "
                "folder. Returns id, name, byte_size, current version number "
                "and folder_id for each file.",
    parameters={
        "type": "object",
        "properties": {
            "space_id": {"type": "integer", "description": "Workspace space id"},
            "folder_id": {"type": "integer", "description": "Optional folder id"},
        },
        "required": ["space_id"],
    },
)
# [RCF:PROTECTED]
async def files_list(ctx: ToolContext, space_id: int, folder_id: int | None = None) -> dict:
    try:
        await require_member(ctx.db, ctx.user_id, space_id)
        query = select(WorkspaceFile).where(
            WorkspaceFile.space_id == space_id,
            WorkspaceFile.deleted_at.is_(None),
        )
        if folder_id is not None:
            query = query.where(WorkspaceFile.folder_id == folder_id)
        result = await ctx.db.execute(query.order_by(WorkspaceFile.name))
        files = result.scalars().all()
        return {
            "status": "success",
            "files": [
                {
                    "id": f.id,
                    "name": f.name,
                    "byte_size": f.byte_size,
                    "version_no": f.current_version_no,
                    "folder_id": f.folder_id,
                }
                for f in files
            ],
        }
    except Exception as e:
        return _error(e)


# [RCF:PROTECTED]
@tool(
    name="files_read",
    description="Read the text content of a workspace file (current or a "
                "specific version). Text files up to 256 KB only; binary or "
                "larger files must be downloaded through the UI.",
    parameters={
        "type": "object",
        "properties": {
            "file_id": {"type": "integer", "description": "Workspace file id"},
            "version_no": {"type": "integer",
                           "description": "Optional specific version to read"},
        },
        "required": ["file_id"],
    },
)
# [RCF:PROTECTED]
async def files_read(ctx: ToolContext, file_id: int, version_no: int | None = None) -> dict:
    try:
        ws_file, member = await _require_file(ctx.db, ctx.user_id, file_id)

        no = version_no if version_no is not None else ws_file.current_version_no
        result = await ctx.db.execute(
            select(FileVersion).where(
                FileVersion.file_id == file_id,
                FileVersion.version_no == no,
            )
        )
        version = result.scalar_one_or_none()
        if version is None:
            return {"status": "error", "message": f"Version {no} not found"}

        data = await media_storage.get_bytes(
            ctx.db, version.uploader_user_id, blob_handle(version.storage_ref),
        )
        if data is None:
            return {"status": "error", "message": "Stored content unavailable"}
        if len(data) > MAX_TOOL_BYTES:
            return {"status": "error",
                    "message": f"File too large to read (limit {MAX_TOOL_BYTES} bytes)"}
        if b"\x00" in data[:1024]:
            return {"status": "error",
                    "message": "Binary file — download it through the UI instead"}

        _add_event(ctx.db, ws_file.id, "downloaded", member.user_id,
                   {"version_no": no, "agent_id": ctx.agent_id}, actor_type="agent")
        await ctx.db.commit()

        return {
            "status": "success",
            "name": ws_file.name,
            "version_no": no,
            "content": data.decode("utf-8", errors="replace"),
        }
    except Exception as e:
        return _error(e)


# [RCF:PROTECTED]
@tool(
    name="files_upload_version",
    description="Add a new version to an existing workspace file with the "
                "given text content (UTF-8, up to 256 KB). The previous "
                "versions stay readable — nothing is ever overwritten.",
    parameters={
        "type": "object",
        "properties": {
            "file_id": {"type": "integer", "description": "Workspace file id"},
            "content": {"type": "string", "description": "Full new text content"},
            "comment": {"type": "string", "description": "Optional change comment"},
        },
        "required": ["file_id", "content"],
    },
)
# [RCF:PROTECTED]
async def files_upload_version(
    ctx: ToolContext, file_id: int, content: str, comment: str | None = None,
) -> dict:
    try:
        if ctx.agent_id is None:
            return {"status": "error", "message": "Only agents may call this tool"}

        ws_file, member = await _require_file(ctx.db, ctx.user_id, file_id, "editor")

        data = content.encode("utf-8")
        if not data:
            return {"status": "error", "message": "Content must not be empty"}
        if len(data) > MAX_TOOL_BYTES:
            return {"status": "error",
                    "message": f"Content too large (limit {MAX_TOOL_BYTES} bytes)"}

        ref = await media_storage.save_bytes(
            ctx.db, ctx.user_id, data, "text/plain", original_filename=ws_file.name,
        )

        new_no = ws_file.current_version_no + 1
        version = FileVersion(
            file_id=file_id,
            version_no=new_no,
            storage_ref=json.dumps(ref),
            byte_size=len(data),
            uploader_user_id=ctx.user_id,
            author_type="agent",
            agent_run_id=ctx.agent_id,
            comment=comment or "Updated by AI assistant",
        )
        ctx.db.add(version)

        ws_file.current_version_no = new_no
        ws_file.byte_size = len(data)
        _add_event(ctx.db, file_id, "version_added", ctx.user_id,
                   {"version_no": new_no, "agent_id": ctx.agent_id},
                   actor_type="agent")
        await _commit_version(ctx.db)

        return {"status": "success", "file_id": file_id, "new_version_no": new_no}
    except Exception as e:
        return _error(e)


# [RCF:PROTECTED]
@tool(
    name="files_move",
    description="Move a workspace file into a folder (folder_id=null moves it "
                "back to the space root).",
    parameters={
        "type": "object",
        "properties": {
            "file_id": {"type": "integer", "description": "Workspace file id"},
            "folder_id": {"type": "integer",
                          "description": "Target folder id, or null for root"},
        },
        "required": ["file_id", "folder_id"],
    },
)
# [RCF:PROTECTED]
async def files_move(ctx: ToolContext, file_id: int, folder_id: int | None) -> dict:
    try:
        ws_file, member = await _require_file(ctx.db, ctx.user_id, file_id, "editor")

        if folder_id is not None:
            result = await ctx.db.execute(
                select(Folder).where(Folder.id == folder_id)
            )
            target = result.scalar_one_or_none()
            if target is None or target.space_id != ws_file.space_id:
                return {"status": "error", "message": "Folder not found in this space"}

        old = ws_file.folder_id
        ws_file.folder_id = folder_id
        _add_event(ctx.db, file_id, "moved", member.user_id,
                   {"from": old, "to": folder_id, "agent_id": ctx.agent_id},
                   actor_type="agent")
        await ctx.db.commit()
        return {"status": "success", "file_id": file_id, "folder_id": folder_id}
    except Exception as e:
        return _error(e)


# [RCF:PROTECTED]
@tool(
    name="files_rename",
    description="Rename a workspace file.",
    parameters={
        "type": "object",
        "properties": {
            "file_id": {"type": "integer", "description": "Workspace file id"},
            "name": {"type": "string", "description": "New file name (1-500 chars)"},
        },
        "required": ["file_id", "name"],
    },
)
# [RCF:PROTECTED]
async def files_rename(ctx: ToolContext, file_id: int, name: str) -> dict:
    try:
        name = name.strip()
        if not name or len(name) > 500:
            return {"status": "error", "message": "Name must be 1-500 characters"}

        ws_file, member = await _require_file(ctx.db, ctx.user_id, file_id, "editor")

        old = ws_file.name
        ws_file.name = name
        _add_event(ctx.db, file_id, "renamed", member.user_id,
                   {"from": old, "to": name, "agent_id": ctx.agent_id},
                   actor_type="agent")
        await ctx.db.commit()
        return {"status": "success", "file_id": file_id, "name": name}
    except Exception as e:
        return _error(e)
