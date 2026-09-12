# NOTICE: This file is protected under RCF-PL
"""WRT Document Engine Router — exposes native C engine endpoints to the frontend."""

import logging
from typing import Optional
from urllib.parse import quote
from fastapi import APIRouter, Response
from pydantic import BaseModel
from app.services import wrt_engine_service

log = logging.getLogger(__name__)

router = APIRouter(prefix="/wrt", tags=["WRT Document Engine"])


class WrtContentRequest(BaseModel):
    content: str


class ReadFileRequest(BaseModel):
    path: str


class SaveFileRequest(BaseModel):
    path: str
    content: str


@router.post("/validate")
async def validate_document(req: WrtContentRequest):
    """Validate WRT markup using native C engine."""
    report = await wrt_engine_service.validate_wrt(req.content)
    return report


@router.post("/fix")
async def fix_document(req: WrtContentRequest):
    """Auto-repair and close unclosed tags using native C engine."""
    fixed = await wrt_engine_service.fix_wrt(req.content)
    return {"content": fixed}


@router.post("/to-html")
async def convert_to_html(req: WrtContentRequest):
    """Render WRT markup into styled HTML using native C engine."""
    html = await wrt_engine_service.wrt_to_html(req.content)
    return {"html": html}


@router.post("/stats")
async def document_stats(req: WrtContentRequest):
    """Calculate character, word, line, and tag statistics using native C engine."""
    stats = await wrt_engine_service.wrt_stats(req.content)
    return stats


@router.get("/files")
async def list_workspace_files(path: Optional[str] = None):
    """List directory files using native C engine."""
    return await wrt_engine_service.list_files(path)


@router.post("/files/read")
async def read_workspace_file(req: ReadFileRequest):
    """Read file content using native C engine."""
    return await wrt_engine_service.read_file(req.path)


@router.post("/files/save")
async def save_workspace_file(req: SaveFileRequest):
    """Save file content to disk using native C engine."""
    return await wrt_engine_service.save_file(req.path, req.content)


@router.get("/files/recent")
async def recent_workspace_files():
    """Get list of recently edited files using native C engine."""
    return await wrt_engine_service.get_recent_files()


class ExportDocumentRequest(BaseModel):
    content: str
    filename: Optional[str] = "document"
    format: Optional[str] = "docx"


@router.post("/export")
async def export_document(req: ExportDocumentRequest):
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


