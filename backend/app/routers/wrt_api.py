# NOTICE: This file is protected under RCF-PL
"""WRT Document Engine Router — exposes native C engine endpoints to the frontend."""

import logging
import os
from typing import Optional
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from app.security import get_current_user
from app.services import wrt_engine_service
from app.models.user import User

log = logging.getLogger(__name__)

router = APIRouter(prefix="/wrt", tags=["WRT Document Engine"])

WORKSPACE_ROOT = "/workspaces/AladdinAI"


def _validate_workspace_path(path: str) -> str:
    """Resolve a path and ensure it stays within WORKSPACE_ROOT."""
    if not path or not path.strip():
        return WORKSPACE_ROOT
    resolved = os.path.realpath(os.path.join(WORKSPACE_ROOT, path))
    if not os.path.commonpath([WORKSPACE_ROOT, resolved]) == WORKSPACE_ROOT:
        raise HTTPException(status_code=400, detail=f"Path is outside workspace root: {path}")
    return resolved


class WrtContentRequest(BaseModel):
    content: str


class ReadFileRequest(BaseModel):
    path: str


class SaveFileRequest(BaseModel):
    path: str
    content: str


@router.post("/validate")
async def validate_document(req: WrtContentRequest, user: User = Depends(get_current_user)):
    """Validate WRT markup using native C engine."""
    report = await wrt_engine_service.validate_wrt(req.content)
    return report


@router.post("/fix")
async def fix_document(req: WrtContentRequest, user: User = Depends(get_current_user)):
    """Auto-repair and close unclosed tags using native C engine."""
    fixed = await wrt_engine_service.fix_wrt(req.content)
    return {"content": fixed}


@router.post("/to-html")
async def convert_to_html(req: WrtContentRequest, user: User = Depends(get_current_user)):
    """Render WRT markup into styled HTML using native C engine."""
    html = await wrt_engine_service.wrt_to_html(req.content)
    return {"html": html}


@router.post("/stats")
async def document_stats(req: WrtContentRequest, user: User = Depends(get_current_user)):
    """Calculate character, word, line, and tag statistics using native C engine."""
    stats = await wrt_engine_service.wrt_stats(req.content)
    return stats


@router.get("/files")
async def list_workspace_files(
    path: Optional[str] = None, user: User = Depends(get_current_user)
):
    """List directory files using native C engine."""
    validated = _validate_workspace_path(path or WORKSPACE_ROOT)
    return await wrt_engine_service.list_files(validated)


@router.post("/files/read")
async def read_workspace_file(
    req: ReadFileRequest, user: User = Depends(get_current_user)
):
    """Read file content using native C engine."""
    validated = _validate_workspace_path(req.path)
    return await wrt_engine_service.read_file(validated)


@router.post("/files/save")
async def save_workspace_file(
    req: SaveFileRequest, user: User = Depends(get_current_user)
):
    """Save file content to disk using native C engine."""
    validated = _validate_workspace_path(req.path)
    return await wrt_engine_service.save_file(validated, req.content)


@router.get("/files/recent")
async def recent_workspace_files(user: User = Depends(get_current_user)):
    """Get list of recently edited files using native C engine."""
    return await wrt_engine_service.get_recent_files()


class ExportDocumentRequest(BaseModel):
    content: str
    filename: Optional[str] = "document"
    format: Optional[str] = "docx"


@router.post("/export")
async def export_document(req: ExportDocumentRequest, user: User = Depends(get_current_user)):
    """Export WRT document content to Word .docx, OpenDocument .odt, PowerPoint .pptx, or .md."""
    fmt = (req.format or "docx").lower().strip(".")
    filename = req.filename or "document"
    base_name = filename.rsplit(".", 1)[0] if "." in filename else filename

    if fmt == "odt":
        from app.services.wrt_engine_service import wrt_to_odt
        data = wrt_to_odt(req.content)
        media_type = "application/vnd.oasis.opendocument.text"
        out_name = f"{base_name}.odt"
    elif fmt == "pptx" or (not fmt and "[slide " in req.content):
        from app.services.wrt_engine_service import wrt_to_pptx
        data = wrt_to_pptx(req.content)
        media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        out_name = f"{base_name}.pptx"
    elif fmt == "md":
        from app.services.wrt_engine_service import wrt_to_md
        data = wrt_to_md(req.content).encode("utf-8")
        media_type = "text/markdown; charset=utf-8"
        out_name = f"{base_name}.md"
    elif fmt == "wrt":
        data = req.content.encode("utf-8")
        media_type = "text/plain; charset=utf-8"
        out_name = f"{base_name}.wrt"
    else:
        from app.services.wrt_engine_service import wrt_to_docx
        data = wrt_to_docx(req.content)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        out_name = f"{base_name}.docx"

    safe_name = out_name.encode("ascii", "ignore").decode() or "document"
    ascii_name = safe_name.replace('"', "").replace("\\", "")
    encoded_name = quote(out_name, safe="")
    disposition = f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{encoded_name}'

    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": disposition},
    )

