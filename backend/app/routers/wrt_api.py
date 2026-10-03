# NOTICE: This file is protected under RCF-PL
"""WRT Document Engine Router — exposes native C engine endpoints to the frontend."""

import logging
import os
from typing import Optional
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from app.security import get_current_user
from app.services.wrt_engine_service import WORKSPACE_ROOT
from app.services import wrt_engine_service
from app.models.user import User

log = logging.getLogger(__name__)

router = APIRouter(prefix="/wrt", tags=["WRT Document Engine"])



def _validate_workspace_path(path: str) -> str:
    """Resolve a path and ensure it stays within WORKSPACE_ROOT."""
    if not path or not path.strip():
        return WORKSPACE_ROOT
    resolved = os.path.realpath(os.path.join(WORKSPACE_ROOT, path))
    if not os.path.commonpath([WORKSPACE_ROOT, resolved]) == WORKSPACE_ROOT:
        raise HTTPException(status_code=400, detail=f"Path is outside workspace root: {path}")
    return resolved


class WrtContentRequest(BaseModel):
    content: str = Field(..., max_length=100_000_000)  # 100 MB limit for self-hosted large docs (pptx, xlsx, images)


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


@router.post("/to-editable-html")
async def convert_to_editable_html(req: WrtContentRequest, user: User = Depends(get_current_user)):
    """Render WRT markup into editable HTML for contentEditable using native C engine."""
    html = await wrt_engine_service.wrt_to_editable_html(req.content)
    return {"html": html}


@router.post("/from-editable-html")
async def convert_from_editable_html(req: WrtContentRequest, user: User = Depends(get_current_user)):
    """Convert editable HTML from contentEditable back to WRT markup using native C engine."""
    wrt = await wrt_engine_service.wrt_from_editable_html(req.content)
    return {"content": wrt}


@router.post("/stats")
async def document_stats(req: WrtContentRequest, user: User = Depends(get_current_user)):
    """Calculate character, word, line, and tag statistics using native C engine."""
    try:
        return await wrt_engine_service.wrt_stats(req.content)
    except wrt_engine_service.WrtEngineUnavailable as e:
        # 503, not 200 with zeros: a zeroed report with valid=True is exactly
        # the shape that let a dead engine read as a healthy one.
        raise HTTPException(status_code=503, detail=str(e))


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

    if fmt == "wrt":
        data = req.content.encode("utf-8")
        media_type = "text/plain; charset=utf-8"
        out_name = f"{base_name}.wrt"
    elif fmt == "md":
        data = (await wrt_engine_service.wrt_to_md(req.content)).encode("utf-8")
        media_type = "text/markdown; charset=utf-8"
        out_name = f"{base_name}.md"
    elif fmt == "odt":
        data = await wrt_engine_service.wrt_to_odt(req.content)
        media_type = "application/vnd.oasis.opendocument.text"
        out_name = f"{base_name}.odt"
    elif fmt == "pptx" or (not fmt and "[slide " in req.content):
        data = await wrt_engine_service.wrt_to_pptx(req.content)
        media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        out_name = f"{base_name}.pptx"
    else:
        data = await wrt_engine_service.wrt_to_docx(req.content)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        out_name = f"{base_name}.docx"

    if not data:
        # Every branch above raises on a failed conversion, so an empty body
        # here means the engine produced nothing. Returning it as a download
        # would hand the user a zero-byte file that looks like a success.
        raise HTTPException(
            status_code=502,
            detail=f"Export to {out_name.rsplit('.', 1)[-1]} produced no data.",
        )

    safe_name = out_name.encode("ascii", "ignore").decode() or "document"
    ascii_name = safe_name.replace('"', "").replace("\\", "")
    encoded_name = quote(out_name, safe="")
    disposition = f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{encoded_name}'

    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": disposition},
    )


# A .pptx with embedded media runs to tens of megabytes; the editor's own
# content limit is 100 MB, so anything past that is a mistake, not a document.
MAX_IMPORT_BYTES = 100 * 1024 * 1024


@router.post("/import")
async def import_document(
    request: Request,
    filename: str = Query(..., max_length=512),
    user: User = Depends(get_current_user),
):
    """Convert an uploaded .docx/.odt/.pptx/.md into WRT for the editor.

    The body is the raw file -- a multi-megabyte .pptx sent as base64 JSON
    would inflate by a third and cost a decode. The format comes from the
    filename in the query string, which is the only thing that reliably
    carries it: browsers set Content-Type inconsistently for Office files, and
    several of them send application/octet-stream.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("docx", "odt", "pptx", "md", "markdown", "txt", "wrt"):
        raise HTTPException(
            status_code=415,
            detail=f"Cannot import .{ext or '?'} — supported: docx, odt, pptx, md.",
        )

    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(body) > MAX_IMPORT_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File is too large to import (limit {MAX_IMPORT_BYTES // (1024 * 1024)} MB).",
        )

    try:
        if ext == "docx":
            content = await wrt_engine_service.docx_to_wrt(body)
        elif ext == "odt":
            content = await wrt_engine_service.odt_to_wrt(body)
        elif ext == "pptx":
            content = await wrt_engine_service.pptx_to_wrt(body)
        else:
            # Markdown, plain text and .wrt itself all take the same path: the
            # engine's md parser is what turns headings/lists/links into WRT.
            content = await wrt_engine_service.md_to_wrt(
                body.decode("utf-8", errors="replace")
            )
    except HTTPException:
        raise
    except Exception as e:
        # A corrupt archive fails deep inside the C reader. 422 says the file
        # itself is bad, which is the one thing the user can act on.
        log.warning("Import of %s failed: %s", filename, e)
        raise HTTPException(
            status_code=422,
            detail=f"Could not read {filename} — the file may be corrupt or password-protected.",
        )

    if not content.strip():
        raise HTTPException(
            status_code=422,
            detail=f"No text could be extracted from {filename}.",
        )

    suggested = filename.rsplit(".", 1)[0] if "." in filename else filename
    return {"content": content, "filename": f"{suggested}.wrt"}

