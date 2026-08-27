// NOTICE: This file is protected under RCF-PL
# MCP Servers — Native Client, Catalog & Agent Bridge

AladdinAI connects to external **MCP (Model Context Protocol)** servers via a
native `httpx` Streamable-HTTP client — no external SDK dependency
(`native-over-oss` doctrine). The integration covers three surfaces:

1. **Native client** (`backend/app/services/mcp_manager.py`) — handshake,
   session caching, SSE + JSON response parsing, capped results.
2. **User-managed servers** (`mcp_servers` table) — per-user, encrypted
   headers at rest, enabled/disabled toggle.
3. **Public catalog** (`CATALOG` — 7 verified stateless servers) — one-click
   install into the user's server list.

Agents access server tools through the bridge (`agent_runner.py`) without
polluting the global tool registry.

---

## 🧩 Naming convention

Every external tool is exposed to agents as:

```
mcp__<server_slug>__<tool_name>
```

`server_slug` is derived from the server name (`re.sub(r"[^a-z0-9]+", "_", ...)`).
The double underscore is the split point: `mcp__deepwiki__resolve_library_id` →
server `deepwiki`, tool `resolve_library_id`. Tools are **not** added to the
global `REGISTRY`; they are assembled dynamically from each enabled server's
`tools_cache` at agent invocation time.

---

## 🔐 Security & isolation

- **User boundary**: `MCPServer.user_id` (FK `users` CASCADE). Every tool call
  checks `user_id == ctx.user_id` and `enabled == true`.
- **Headers**: stored encrypted (`headers_encrypted` via `crypto.encrypt`).
  The API never returns header values — only key names (`header_names`).
- **Results**: capped at 256 KB (`MAX_RESULT_BYTES`). Oversized tool schemas
  (> 8 KB) are skipped; per-server tool lists capped at 100.
- **Sessions**: in-memory per `(user_id, server_id)` with 600 s TTL. A 404
  triggers exactly one clean re-initialize; a second expiry propagates as
  `{"status": "error", ...}`.

---

## 📚 Catalog (`GET /mcp/catalog`)

Seven verified public stateless servers (no auth required except GitHub):

| Name | URL | Category | Description |
|---|---|---|---|
| DeepWiki | `https://mcp.deepwiki.com/mcp` | documentation | Open-source repo structure & usage |
| Context7 | `https://mcp.context7.com/mcp` | documentation | Library docs pulled into agent context |
| Exa | `https://mcp.exa.ai/mcp` | search | Web search + page fetch for agents |
| Microsoft Learn | `https://learn.microsoft.com/api/mcp` | documentation | Official MS docs & catalog |
| AWS Knowledge | `https://knowledge-mcp.global.api.aws/mcp` | documentation | AWS docs, region, availability |
| Hugging Face | `https://huggingface.co/mcp` | ml | Models, datasets, spaces |
| GitHub | `https://api.githubcopilot.com/mcp/` | development | Repos, PRs, code search (requires `Authorization` header) |

Install: Settings → MCP Servers → Catalog → Install. Servers needing auth
(prefilled header with `headers_hint`) open the add form instead of direct
creation.

---

## ⚙️ Agent bridge (`agent_runner.py`)

Before the filter (`line 253`):

- Read `agent.tools_config.get("mcp_servers", [])`.
- Select user's enabled servers matching those IDs.
- Build OpenAI `function` schemas from each server's `tools_cache`.
- Merge into `allowed` schemas; pass via `ToolContext(extra={...})`.

Execution (`_execute_mcp_call`):

- `name.startswith("mcp__")` → split on first `__`.
- Resolve server by slug against allowed IDs; unknown slug → error.
- Call `mcp_manager.call_tool()`; result mapped to `{"status":"success",...}`
  or `{"error":"..."}`.

---

## 🗂️ Where things live

| Path | Role |
|---|---|
| `backend/app/models/mcp_server.py` | SQLAlchemy model (`mcp_servers`) |
| `backend/app/services/mcp_manager.py` | Native client, session cache, `CATALOG`, encryption |
| `backend/app/routers/mcp.py` | REST: servers CRUD, test, tools (cached), catalog |
| `backend/app/services/agent_runner.py` | Bridge: schema assembly + `mcp__` dispatch |
| `frontend/src/components/settings/McpSettings.tsx` | Settings tab + catalog install |
| `backend/alembic/versions/b8e2f4a61c93_create_mcp_servers.py` | Migration (table guard) |

Design rationale (native `httpx` over SDK, Streamable-HTTP-only transport,
stateless server sentinel, cap convention) is consistent with
`docs/adr/0010-native-agent-meta-search.md` and `0012-pluggable-image-gen-backends.md`.
