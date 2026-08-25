# NOTICE: This file is protected under RCF-PL
"""User-scoped MCP (Model Context Protocol) server management.

Servers are per-user records pointing at Streamable HTTP endpoints. Header
values (auth tokens) are accepted in plaintext over the API, encrypted at
rest via app.crypto, and never returned to any client — responses carry only
header NAMES. `POST /{id}/test` performs a live tools/list and refreshes the
cached tool catalog that agent runners build schemas from.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.mcp_server import MCPServer
from app.models.user import User
from app.schemas.mcp import (
    CatalogEntry,
    McpServerCreate,
    McpServerResponse,
    McpServerUpdate,
    McpTestResult,
)
from app.security import get_current_user
from app.services import mcp_manager

log = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["mcp"])


def _to_response(server: MCPServer) -> dict:
    header_names = (
        sorted(mcp_manager.decrypt_headers_blob(server.headers_encrypted).keys())
        if server.headers_encrypted else []
    )
    return {
        "id": server.id,
        "name": server.name,
        "url": server.url,
        "enabled": server.enabled,
        "timeout_seconds": server.timeout_seconds,
        "header_names": header_names,
        "tools": server.tools_cache or [],
        "last_checked_at": server.last_checked_at,
        "created_at": server.created_at,
        "updated_at": server.updated_at,
    }


async def _owned_server(server_id: int, user: User, db: AsyncSession) -> MCPServer:
    result = await db.execute(
        select(MCPServer).where(MCPServer.id == server_id, MCPServer.user_id == user.id)
    )
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return server


async def _ensure_slug_free(
    db: AsyncSession, user_id: int, name: str, exclude_id: int | None = None,
) -> None:
    """Tool prefixes are built from name slugs — two same-slug servers would
    collide into identical `mcp__<slug>__` tool names. Reject up front."""
    slug = mcp_manager.server_slug(name)
    result = await db.execute(
        select(MCPServer).where(MCPServer.user_id == user_id)
    )
    for other in result.scalars().all():
        if other.id != exclude_id and mcp_manager.server_slug(other.name) == slug:
            raise HTTPException(
                status_code=422,
                detail=f"A server named '{other.name}' already produces the "
                f"tool prefix '{slug}' — pick a distinct name",
            )


@router.get("/catalog", response_model=list[CatalogEntry])
async def get_catalog(user: User = Depends(get_current_user)):
    """Curated public MCP servers («стор-lite») for one-click install."""
    return mcp_manager.catalog_entries()


@router.get("/servers", response_model=list[McpServerResponse])
async def list_servers(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MCPServer).where(MCPServer.user_id == user.id))
    return [_to_response(s) for s in result.scalars().all()]


@router.post("/servers", response_model=McpServerResponse, status_code=201)
async def create_server(
    body: McpServerCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    if not body.url.lower().startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="URL must be http(s)")
    await _ensure_slug_free(db, user.id, body.name.strip())
    server = MCPServer(
        user_id=user.id,
        name=body.name.strip(),
        url=body.url.strip(),
        headers_encrypted=mcp_manager.encrypt_headers(body.headers or {}),
        timeout_seconds=body.timeout_seconds,
    )
    db.add(server)
    await db.commit()
    await db.refresh(server)
    mcp_manager.invalidate_sessions(user.id, server.id)
    return _to_response(server)


@router.patch("/servers/{server_id}", response_model=McpServerResponse)
async def update_server(
    server_id: int,
    body: McpServerUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    server = await _owned_server(server_id, user, db)
    if body.name is not None:
        new_name = body.name.strip()
        if new_name != server.name:
            await _ensure_slug_free(db, user.id, new_name, exclude_id=server.id)
        server.name = new_name
    if body.url is not None:
        if not body.url.lower().startswith(("http://", "https://")):
            raise HTTPException(status_code=422, detail="URL must be http(s)")
        server.url = body.url.strip()
    if body.enabled is not None:
        server.enabled = body.enabled
    if body.timeout_seconds is not None:
        server.timeout_seconds = body.timeout_seconds
    if body.headers is not None:
        server.headers_encrypted = mcp_manager.encrypt_headers(body.headers)
    await db.commit()
    await db.refresh(server)
    mcp_manager.invalidate_sessions(user.id, server.id)
    return _to_response(server)


@router.delete("/servers/{server_id}", status_code=204)
async def delete_server(
    server_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    server = await _owned_server(server_id, user, db)
    await db.delete(server)
    await db.commit()
    mcp_manager.invalidate_sessions(user.id, server.id)


@router.get("/servers/{server_id}/tools", response_model=list)
async def get_tools(
    server_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    """Cached tool list (what agents would see) without a live round-trip."""
    server = await _owned_server(server_id, user, db)
    return server.tools_cache or []


@router.post("/servers/{server_id}/test", response_model=McpTestResult)
async def test_server(
    server_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    """Live tools/list; refreshes the cache so agents pick up new tools."""
    server = await _owned_server(server_id, user, db)
    try:
        tools = await mcp_manager.fetch_tools(server, user.id)
    except mcp_manager.McpError as e:
        return McpTestResult(status="error", message=str(e))
    server.tools_cache = tools
    server.last_checked_at = datetime.now(timezone.utc)
    await db.commit()
    return McpTestResult(status="success", tools=[t["name"] for t in tools])
