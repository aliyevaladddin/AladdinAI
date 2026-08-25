# NOTICE: This file is protected under RCF-PL v2.0.3
"""Native MCP (Model Context Protocol) client — Streamable HTTP transport.

Implements just enough of the MCP spec to talk to stateless Streamable HTTP
servers without pulling in the official SDK (native-over-bolton doctrine):

    initialize handshake → notifications/initialized → tools/list → tools/call

Servers answer either `application/json` or an SSE (`text/event-stream`)
stream; both shapes are parsed here. A server may issue an `MCP-Session-Id`
header — it is cached in memory per (user, server) and re-established once
if the server answers 404 (expired session). Servers that never hand out a
session id are treated as stateless and simply never send one back.

Every failure surfaces through the registry's error convention:
`{"status": "error", "message": ...}` — agents see a sentence, not a traceback.

Tool results are capped at MAX_RESULT_BYTES so one external server cannot
flood the model context.
"""
from __future__ import annotations

import json
import logging
import re
import time
import uuid

import httpx
from sqlalchemy import select

from app.crypto import encrypt, decrypt
from app.models.mcp_server import MCPServer

log = logging.getLogger(__name__)

PROTOCOL_VERSION = "2025-06-18"
CLIENT_INFO = {"name": "aladdinai", "version": "1.0"}
MAX_RESULT_BYTES = 256 * 1024
SESSION_TTL_SECONDS = 600
# Per-server tool-catalog caps: one hostile/buggy server must not be able to
# flood the model context (or this column) with thousands of definitions.
MAX_TOOLS_PER_SERVER = 100
MAX_TOOL_SCHEMA_BYTES = 8 * 1024

# In-process session cache: (user_id, server_id) -> (session_id, acquired_at).
# A stored "" means "stateless server, handshake already done" — no header
# is sent, but we skip re-initializing within the TTL.
_sessions: dict[tuple[int, int], tuple[str, float]] = {}

# [RCF:PROTECTED]
class McpError(Exception):
    """Protocol/transport failure with a user-presentable message."""


class SessionExpired(McpError):
    """The server rejected our MCP-Session-Id (404); safe to re-initialize."""


def _decrypt_headers(server: MCPServer) -> dict[str, str]:
    if not server.headers_encrypted:
        return {}
    return decrypt_headers_blob(server.headers_encrypted)


def server_slug(name: str) -> str:
    """Stable tool-name prefix component: 'GitHub Tools' → 'github_tools'."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or "server"


# ── wire helpers ─────────────────────────────────────────────────────────────


def _parse_sse(text: str) -> list[dict]:
    """Extract the JSON payloads from an SSE body (data: lines)."""
    # Normalize CRLF first — real servers (sse_starlette, the MCP SDK) end
    # events with \r\n\r\n, which plain "\n\n" splitting would never split.
    messages: list[dict] = []
    for chunk in text.replace("\r\n", "\n").split("\n\n"):
        data_lines = [
            line[5:].strip() for line in chunk.splitlines()
            if line.startswith("data:")
        ]
        if not data_lines:
            continue
        try:
            messages.append(json.loads("\n".join(data_lines)))
        except json.JSONDecodeError:
            continue
    return messages


def _extract_response(body: str, content_type: str, request_id: int) -> dict:
    """Return the JSON-RPC object answering `request_id` (result or error).

    Some real servers (Microsoft Learn, Hugging Face) omit the `id` echo on
    responses entirely; when nothing matches by id, fall back to the single
    result/error message rather than failing the call.
    """
    if "text/event-stream" in content_type:
        candidates = [m for m in _parse_sse(body) if isinstance(m, dict)]
    else:
        try:
            first = json.loads(body)
        except json.JSONDecodeError as e:
            raise McpError(f"Invalid response from MCP server: {e}") from e
        candidates = first if isinstance(first, list) else [first]
        candidates = [m for m in candidates if isinstance(m, dict)]

    answers = [m for m in candidates if "result" in m or "error" in m]
    for msg in answers:
        if msg.get("id") == request_id:
            return msg
    if len(answers) == 1:
        return answers[0]
    raise McpError("MCP server did not answer the request")


async def _rpc(
    server: MCPServer,
    method: str,
    params: dict | None = None,
    *,
    notify: bool = False,
    session_id: str | None = None,
    transport: httpx.AsyncTransport | None = None,
) -> tuple[dict | None, str | None]:
    """POST one JSON-RPC message. Returns (result, session_id_from_headers).

    Notifications get no response parsed — anything ≤3xx counts as delivered.
    """
    request_id = int(uuid.uuid4().int & 0x7FFFFFFF)
    payload: dict = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        payload["params"] = params
    if not notify:
        payload["id"] = request_id

    headers = {
        **_decrypt_headers(server),
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    if session_id:
        headers["MCP-Session-Id"] = session_id

    try:
        async with httpx.AsyncClient(
            transport=transport, timeout=server.timeout_seconds, follow_redirects=True,
        ) as client:
            resp = await client.post(server.url, json=payload, headers=headers)
    except httpx.HTTPError as e:
        raise McpError(f"MCP server unreachable: {e}") from e

    new_session = resp.headers.get("MCP-Session-Id") or session_id
    if resp.status_code == 404 and session_id:
        raise SessionExpired("MCP session expired")
    if resp.status_code >= 400:
        raise McpError(f"MCP server returned HTTP {resp.status_code}")
    if notify:
        return None, new_session

    msg = _extract_response(resp.text, resp.headers.get("content-type", ""), request_id)
    if "error" in msg:
        err = msg["error"] or {}
        raise McpError(str(err.get("message") or err))
    return msg.get("result"), new_session


async def _ensure_session(
    server: MCPServer,
    user_id: int,
    transport: httpx.AsyncTransport | None = None,
) -> str | None:
    """Return the cached session id or run the initialize handshake."""
    now = time.monotonic()
    # Opportunistic TTL sweep keeps the process-wide dict bounded.
    for k in [k for k, v in _sessions.items() if now - v[1] >= SESSION_TTL_SECONDS]:
        _sessions.pop(k, None)

    key = (user_id, server.id)
    cached = _sessions.get(key)
    if cached and now - cached[1] < SESSION_TTL_SECONDS:
        return cached[0]

    result, sid = await _rpc(
        server, "initialize",
        {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": CLIENT_INFO,
        },
        transport=transport,
    )
    # Stateful servers want the initialized notification before other calls.
    try:
        await _rpc(
            server, "notifications/initialized", notify=True,
            session_id=sid, transport=transport,
        )
    except McpError:
        pass  # stateless servers may reject/ignore it entirely
    # Cache even a None session as "" — the handshake happened; stateless
    # servers are not re-initialized on every call within the TTL.
    _sessions[key] = (sid or "", time.monotonic())
    log.debug("MCP init %s: %s", server.name, (result or {}).get("serverInfo"))
    return sid


async def _with_session(
    server: MCPServer,
    user_id: int,
    method: str,
    params: dict,
    transport: httpx.AsyncTransport | None = None,
) -> dict:
    """Call a method, retrying exactly once if the session went stale."""
    sid = await _ensure_session(server, user_id, transport=transport)
    try:
        result, _ = await _rpc(
            server, method, params=params, session_id=sid, transport=transport,
        )
    except SessionExpired:
        # Exactly one clean re-initialize; a second expiry propagates.
        _sessions.pop((user_id, server.id), None)
        sid = await _ensure_session(server, user_id, transport=transport)
        result, _ = await _rpc(
            server, method, params=params, session_id=sid, transport=transport,
        )
    return result or {}


# ── public surface ───────────────────────────────────────────────────────────


def _normalize_tools(raw_tools: list) -> list[dict]:
    out: list[dict] = []
    for t in raw_tools:
        if not (isinstance(t, dict) and t.get("name")):
            continue
        schema = t.get("inputSchema") or {"type": "object", "properties": {}}
        try:
            if len(json.dumps(schema)) > MAX_TOOL_SCHEMA_BYTES:
                continue  # oversized definition — skip rather than flood context
        except (TypeError, ValueError):
            continue
        out.append({
            "name": str(t["name"]),
            "description": str(t.get("description") or ""),
            "inputSchema": schema,
        })
        if len(out) >= MAX_TOOLS_PER_SERVER:
            break
    return out


async def fetch_tools(
    server: MCPServer,
    user_id: int,
    *,
    transport: httpx.AsyncTransport | None = None,
) -> list[dict]:
    """Live tools/list against the server."""
    result = await _with_session(server, user_id, "tools/list", {}, transport=transport)
    return _normalize_tools(result.get("tools") or [])


async def test_connection(
    server: MCPServer,
    user_id: int,
    *,
    transport: httpx.AsyncTransport | None = None,
) -> list[str]:
    """Names of the tools the server exposes — used by the Test button."""
    tools = await fetch_tools(server, user_id, transport=transport)
    return [t["name"] for t in tools]


def _content_to_text(content_blocks: list) -> str:
    parts: list[str] = []
    for block in content_blocks if isinstance(content_blocks, list) else []:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text") or ""))
        elif isinstance(block, dict) and block.get("type") == "resource":
            res = block.get("resource") or {}
            parts.append(str(res.get("text") or ""))
    return "\n".join(parts)


async def call_tool(
    db,
    user_id: int,
    server_id: int,
    tool_name: str,
    arguments: dict,
    *,
    transport: httpx.AsyncTransport | None = None,
) -> dict:
    """Execute one tool on one of the user's enabled servers.

    The ownership/enabled check here is the security boundary — callers must
    pass ids taken from the *chatting* user's config, never raw model output.
    """
    server = (
        await db.execute(
            select(MCPServer).where(
                MCPServer.id == server_id, MCPServer.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if server is None:
        return {"status": "error", "message": "Unknown MCP server"}
    if not server.enabled:
        return {"status": "error", "message": f"MCP server '{server.name}' is disabled"}

    try:
        result = await _with_session(
            server, user_id, "tools/call",
            {"name": tool_name, "arguments": arguments or {}},
            transport=transport,
        )
    except McpError as e:
        return {"status": "error", "message": str(e)}

    text = _content_to_text(result.get("content") or [])
    if not text and isinstance(result.get("structuredContent"), dict):
        text = json.dumps(result["structuredContent"], default=str)
    if not text:
        text = "(empty result)"

    encoded = text.encode("utf-8", errors="replace")
    truncated = len(encoded) > MAX_RESULT_BYTES
    if truncated:
        text = encoded[:MAX_RESULT_BYTES].decode("utf-8", errors="ignore") + "\n…[truncated]"

    out = {"status": "success", "result": text}
    if result.get("isError"):
        out["is_error"] = True
    if truncated:
        out["truncated"] = True
    return out


def encrypt_headers(headers: dict[str, str]) -> str | None:
    """Whole-dict encryption for at-rest storage; None when empty."""
    clean = {k: v for k, v in (headers or {}).items() if k and v}
    return encrypt(json.dumps(clean)) if clean else None


def decrypt_headers_blob(blob: str) -> dict[str, str]:
    """Inverse of :func:`encrypt_headers`; tolerant of corrupt rows."""
    try:
        data = json.loads(decrypt(blob))
        return {str(k): str(v) for k, v in data.items() if v is not None}
    except Exception:  # noqa: BLE001
        log.exception("Failed to decrypt an MCP headers blob")
        return {}


def invalidate_sessions(user_id: int, server_id: int) -> None:
    _sessions.pop((user_id, server_id), None)


# ── catalog («стор-lite») ────────────────────────────────────────────────────
# Curated public Streamable-HTTP servers. Every entry was verified reachable
# at the time it was added; entries needing an account carry `headers_hint`.

CATALOG: list[dict] = [
    {
        "name": "DeepWiki",
        "url": "https://mcp.deepwiki.com/mcp",
        "category": "documentation",
        "description": "Ask questions about any open-source repository — structure, usage, internals.",
        "headers_hint": {},
    },
    {
        "name": "Microsoft Learn",
        "url": "https://learn.microsoft.com/api/mcp",
        "category": "documentation",
        "description": "Official Microsoft documentation and Learn catalog search.",
        "headers_hint": {},
    },
    {
        "name": "Hugging Face",
        "url": "https://huggingface.co/mcp",
        "category": "ml",
        "description": "Search models, datasets and spaces on Hugging Face.",
        "headers_hint": {},
    },
    {
        "name": "GitHub",
        "url": "https://api.githubcopilot.com/mcp/",
        "category": "development",
        "description": "Repositories, issues, pull requests and code search via your GitHub token.",
        "headers_hint": {"Authorization": "Bearer ghp_your_token"},
    },
]


def catalog_entries() -> list[dict]:
    return CATALOG
