# NOTICE: This file is protected under RCF-PL v2.0.3
"""Tests for the native MCP client, its REST surface and the agent-runner bridge.

A fake Streamable-HTTP MCP server runs inside ``httpx.MockTransport``; tests
cover both wire shapes seen in the wild (plain JSON and SSE, with and without
the ``id`` echo some servers omit), plus the security contract:

  * header VALUES never appear in any API response,
  * tool calls re-check ownership/enabled against the chatting user,
  * MCP tools stay out of the global REGISTRY,
  * oversized results are truncated, failures surface as
    ``{"status": "error", "message": ...}``.
"""
import asyncio
import json
import time

import httpx
import pytest

from app.services import mcp_manager
from app.tools.base import REGISTRY, ToolContext


# ── fake MCP server ──────────────────────────────────────────────────────────


class FakeMCP:
    """Stateful-enough fake: counts initializes, optionally hands out sessions."""

    def __init__(
        self,
        *,
        sse: bool = False,
        omit_id: bool = False,
        tools: list[dict] | None = None,
        call_text: str = "42 files created",
        call_error: bool = False,
        empty_call: bool = False,
        structured_only: bool = False,
        http_fail_status: int | None = None,
        garbage: bool = False,
        session_mode: bool = False,
        huge_result: bool = False,
    ):
        self.sse = sse
        self.omit_id = omit_id
        self.tools = tools if tools is not None else [
            {
                "name": "create_issue",
                "description": "Create a repository issue",
                "inputSchema": {
                    "type": "object",
                    "properties": {"title": {"type": "string"}},
                    "required": ["title"],
                },
            },
            {"name": "list_repos", "description": "List repositories",
             "inputSchema": {"type": "object", "properties": {}}},
        ]
        self.call_text = call_text
        self.call_error = call_error
        self.empty_call = empty_call
        self.structured_only = structured_only
        self.http_fail_status = http_fail_status
        self.garbage = garbage
        self.session_mode = session_mode
        self.huge_result = huge_result
        self.init_count = 0
        self.list_count = 0
        self.call_count = 0
        self.last_arguments: dict | None = None
        self._session_counter = 0
        self._current_session: str | None = None

    # -- wire helpers --

    def _respond(self, request_payload: dict, result) -> httpx.Response:
        body: dict = {"jsonrpc": "2.0", "result": result}
        if not self.omit_id:
            body["id"] = request_payload.get("id")
        text = json.dumps(body)
        if self.garbage:
            text = "<<not json>>"
        if self.sse:
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=f"event: message\ndata: {text}\n\n".encode(),
            )
        return httpx.Response(
            200, headers={"content-type": "application/json"}, content=text.encode(),
        )

    def handler(self, request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        method = payload.get("method")

        if self.http_fail_status is not None and method != "initialize":
            return httpx.Response(self.http_fail_status)

        # Session enforcement (stateful-server simulation): only the latest
        # issued session id is accepted.
        if method == "initialize":
            self.init_count += 1
        if self.session_mode and method == "initialize":
            self._session_counter += 1
            self._current_session = f"sess-{self._session_counter}"
            resp = self._respond(payload, {"protocolVersion": "2025-06-18", "serverInfo": {}})
            resp.headers["MCP-Session-Id"] = self._current_session
            return resp
        if self.session_mode and method != "notifications/initialized":
            if request.headers.get("MCP-Session-Id") != self._current_session:
                return httpx.Response(404)

        if method == "notifications/initialized":
            return httpx.Response(202)
        if method == "tools/list":
            self.list_count += 1
            return self._respond(payload, {"tools": self.tools})
        if method == "tools/call":
            self.call_count += 1
            params = payload.get("params") or {}
            self.last_arguments = params.get("arguments")
            if self.huge_result:
                text = "x" * (mcp_manager.MAX_RESULT_BYTES + 1024)
            else:
                text = self.call_text
            result: dict = {"content": [{"type": "text", "text": text}]}
            if self.call_error:
                result["isError"] = True
            if self.empty_call:
                result["content"] = []
            if self.structured_only:
                result["content"] = []
                result["structuredContent"] = {"rows": 7}
            return self._respond(payload, result)
        return self._respond(payload, {})


@pytest.fixture(autouse=True)
def _clean_sessions():
    mcp_manager._sessions.clear()
    yield
    mcp_manager._sessions.clear()


def use_fake_server(monkeypatch, fake: FakeMCP) -> None:
    """Route every AsyncClient mcp_manager opens during this test to the fake."""
    transport = httpx.MockTransport(fake.handler)
    real_cls = httpx.AsyncClient

    class PatchedAsyncClient(real_cls):
        def __init__(self, *args, **kwargs):
            if kwargs.get("transport") is None:
                kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", PatchedAsyncClient)


# ── helpers ──────────────────────────────────────────────────────────────────


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_server(client, auth_headers, *, name="My Server", url="https://fake.example/mcp",
                 headers=None, enabled=None) -> dict:
    body: dict = {"name": name, "url": url}
    if headers is not None:
        body["headers"] = headers
    r = client.post("/api/mcp/servers", json=body, headers=auth_headers)
    assert r.status_code == 201, r.text
    return r.json()


# ── CRUD + secrecy ───────────────────────────────────────────────────────────


def test_server_crud_and_header_secrecy(client, auth_headers):
    created = _make_server(
        client, auth_headers,
        headers={"Authorization": "Bearer super-secret-token"},
    )
    assert created["header_names"] == ["Authorization"]
    assert "super-secret-token" not in json.dumps(created)

    listed = client.get("/api/mcp/servers", headers=auth_headers).json()
    assert [s["name"] for s in listed] == ["My Server"]
    assert "super-secret-token" not in json.dumps(listed)

    upd = client.patch(
        f"/api/mcp/servers/{created['id']}", json={"enabled": False},
        headers=auth_headers,
    )
    assert upd.status_code == 200 and upd.json()["enabled"] is False

    assert client.delete(f"/api/mcp/servers/{created['id']}", headers=auth_headers).status_code == 204
    assert client.get("/api/mcp/servers", headers=auth_headers).json() == []


def test_server_rejects_non_http_url_and_other_users_servers(client, auth_headers):
    r = client.post("/api/mcp/servers", json={"name": "X", "url": "ftp://nope"},
                    headers=auth_headers)
    assert r.status_code == 422

    # Another tenant sees neither list entries nor direct access.
    other = _make_server(client, auth_headers)
    email = f"other-{__import__('uuid').uuid4().hex[:8]}@example.com"
    reg = client.post("/api/auth/register",
                      json={"email": email, "password": "testpassword123", "name": "Other"})
    other_headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    assert client.get("/api/mcp/servers", headers=other_headers).json() == []
    assert client.get(f"/api/mcp/servers/{other['id']}/tools",
                      headers=other_headers).status_code == 404


def test_catalog_endpoint(client, auth_headers):
    entries = client.get("/api/mcp/catalog", headers=auth_headers).json()
    assert len(entries) >= 3
    for e in entries:
        assert set(e) >= {"name", "url", "description", "headers_hint"}


# ── live protocol through the router ─────────────────────────────────────────


def test_test_endpoint_refreshes_cache(monkeypatch, client, auth_headers):
    fake = FakeMCP(sse=True)
    use_fake_server(monkeypatch, fake)
    server = _make_server(client, auth_headers)

    r = client.post(f"/api/mcp/servers/{server['id']}/test", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert data["tools"] == ["create_issue", "list_repos"]

    cached = client.get(f"/api/mcp/servers/{server['id']}/tools", headers=auth_headers).json()
    assert [t["name"] for t in cached] == ["create_issue", "list_repos"]
    assert fake.init_count == 1  # handshake ran exactly once for both calls


def test_test_endpoint_reports_errors_as_200(monkeypatch, client, auth_headers):
    fake = FakeMCP(garbage=True)
    use_fake_server(monkeypatch, fake)
    server = _make_server(client, auth_headers)

    data = client.post(f"/api/mcp/servers/{server['id']}/test", headers=auth_headers).json()
    assert data["status"] == "error"
    assert data["message"]


# ── manager: sessions, shapes, caps ──────────────────────────────────────────


def test_session_cached_and_reinit_on_expiry(monkeypatch, db_session):
    fake = FakeMCP(session_mode=True)
    use_fake_server(monkeypatch, fake)

    async def scenario(db):
        server = mcp_manager.MCPServer(name="S", url="https://s.example/mcp", user_id=1)
        db.add(server)
        await db.commit()
        await db.refresh(server)

        await mcp_manager.fetch_tools(server, 1)
        await mcp_manager.fetch_tools(server, 1)
        assert fake.init_count == 1  # second call reused the cached session
        assert fake.list_count == 2

        # Simulate a session the server no longer knows: next list 404s and
        # the client must re-initialize exactly once, then succeed.
        key = (1, server.id)
        old_sid = mcp_manager._sessions[key][0]
        mcp_manager._sessions[key] = ("sess-stale", time.monotonic())
        assert old_sid != "sess-stale"
        await mcp_manager.fetch_tools(server, 1)
        assert fake.init_count == 2
        assert mcp_manager._sessions[key][0].startswith("sess-")

    _run(scenario(db_session))


def test_id_less_responses_accepted(monkeypatch, db_session):
    """Microsoft Learn / Hugging Face omit the `id` echo — still parseable."""
    fake = FakeMCP(omit_id=True)
    use_fake_server(monkeypatch, fake)

    async def scenario(db):
        server = mcp_manager.MCPServer(name="Learn", url="https://l.example/api/mcp", user_id=1)
        db.add(server)
        await db.commit()
        await db.refresh(server)
        tools = await mcp_manager.fetch_tools(server, 1)
        assert [t["name"] for t in tools] == ["create_issue", "list_repos"]

    _run(scenario(db_session))


def test_call_tool_caps_and_flags(monkeypatch, db_session):
    fake = FakeMCP(huge_result=True)
    use_fake_server(monkeypatch, fake)

    async def scenario(db):
        server = mcp_manager.MCPServer(name="Big", url="https://b.example/mcp", user_id=7)
        db.add(server)
        await db.commit()
        await db.refresh(server)
        out = await mcp_manager.call_tool(db, 7, server.id, "create_issue", {"title": "t"})
        assert out["status"] == "success"
        assert out["truncated"] is True
        assert len(out["result"].encode()) <= mcp_manager.MAX_RESULT_BYTES + 64

    _run(scenario(db_session))


def test_call_tool_empty_and_structured_fallbacks(monkeypatch, db_session):
    async def scenario(db):
        server = mcp_manager.MCPServer(name="F", url="https://f.example/mcp", user_id=3)
        db.add(server)
        await db.commit()
        await db.refresh(server)

        empty = FakeMCP(empty_call=True)
        use_fake_server(monkeypatch, empty)
        out = await mcp_manager.call_tool(db, 3, server.id, "create_issue", {})
        assert out["result"] == "(empty result)"

        struct = FakeMCP(structured_only=True)
        use_fake_server(monkeypatch, struct)
        out = await mcp_manager.call_tool(db, 3, server.id, "create_issue", {})
        assert "rows" in out["result"]

    _run(scenario(db_session))


def test_call_tool_is_error_passthrough(monkeypatch, db_session):
    fake = FakeMCP(call_error=True)
    use_fake_server(monkeypatch, fake)

    async def scenario(db):
        server = mcp_manager.MCPServer(name="E", url="https://e.example/mcp", user_id=9)
        db.add(server)
        await db.commit()
        await db.refresh(server)
        out = await mcp_manager.call_tool(db, 9, server.id, "create_issue", {})
        assert out["status"] == "success" and out["is_error"] is True

    _run(scenario(db_session))


def test_call_tool_http_failure_convention(monkeypatch, db_session):
    fake = FakeMCP(http_fail_status=503)
    use_fake_server(monkeypatch, fake)

    async def scenario(db):
        server = mcp_manager.MCPServer(name="Down", url="https://d.example/mcp", user_id=11)
        db.add(server)
        await db.commit()
        await db.refresh(server)
        out = await mcp_manager.call_tool(db, 11, server.id, "create_issue", {})
        assert out["status"] == "error"
        assert "HTTP 503" in out["message"]

    _run(scenario(db_session))


def test_call_tool_tenant_isolation_and_disabled(db_session):
    async def scenario(db):
        mine = mcp_manager.MCPServer(name="Mine", url="https://m.example/mcp", user_id=21)
        foreign = mcp_manager.MCPServer(name="Foreign", url="https://o.example/mcp", user_id=99)
        off = mcp_manager.MCPServer(name="Off", url="https://x.example/mcp", user_id=21, enabled=False)
        db.add_all([mine, foreign, off])
        await db.commit()
        for s in (mine, foreign, off):
            await db.refresh(s)

        out = await mcp_manager.call_tool(db, 21, foreign.id, "create_issue", {})
        assert out == {"status": "error", "message": "Unknown MCP server"}

        out = await mcp_manager.call_tool(db, 21, off.id, "create_issue", {})
        assert out["status"] == "error" and "disabled" in out["message"]

        out = await mcp_manager.call_tool(db, 999999, mine.id, "create_issue", {})
        assert out == {"status": "error", "message": "Unknown MCP server"}

    _run(scenario(db_session))


def test_slug_and_header_crypto():
    assert mcp_manager.server_slug("GitHub Tools!") == "github_tools"
    assert mcp_manager.server_slug("---") == "server"

    blob = mcp_manager.encrypt_headers({"Authorization": "Bearer tok"})
    assert "tok" not in blob
    assert mcp_manager.decrypt_headers_blob(blob) == {"Authorization": "Bearer tok"}
    assert mcp_manager.encrypt_headers({}) is None
    assert mcp_manager.decrypt_headers_blob("garbage") == {}


# ── agent-runner bridge ──────────────────────────────────────────────────────


async def _make_server_row(db, *, name="Repo Tools", user_id=31, enabled=True, cache=True):
    server = mcp_manager.MCPServer(
        name=name, url=f"https://{name.lower().replace(' ', '')}.example/mcp",
        user_id=user_id,
        enabled=enabled,
        tools_cache=[
            {
                "name": "create_issue", "description": "Create an issue",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ] if cache else None,
    )
    db.add(server)
    await db.commit()
    await db.refresh(server)
    return server


async def _make_agent(db, user_id=31, *, mcp_ids=None):
    from app.models.agent import Agent

    agent = Agent(
        name="A", role="dev", model="test-model", system_prompt="p",
        user_id=user_id, tools_config={"allowed": [], "mcp_servers": mcp_ids or []},
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


def test_bridge_schemas_gated_by_config(db_session):
    async def scenario(db):
        from app.services.agent_runner import _mcp_schemas

        # No MCP config at all → nothing.
        bare = await _make_agent(db, mcp_ids=None)
        assert await _mcp_schemas(db, bare) == []

        server = await _make_server_row(db)

        # Referenced + enabled + same owner → one schema, prefixed name.
        agent = await _make_agent(db, mcp_ids=[server.id])
        schemas = await _mcp_schemas(db, agent)
        assert len(schemas) == 1
        fn = schemas[0]["function"]
        assert fn["name"] == "mcp__repo_tools__create_issue"
        assert fn["description"] == "Create an issue"
        assert fn["parameters"]["type"] == "object"
        # Nothing leaked into the global registry.
        assert "mcp__repo_tools__create_issue" not in REGISTRY

        # Server without a refreshed cache contributes nothing.
        empty_server = await _make_server_row(db, name="No Cache", cache=False)
        agent2 = await _make_agent(db, mcp_ids=[empty_server.id])
        assert await _mcp_schemas(db, agent2) == []

        # Disabled server contributes nothing even when referenced.
        off_server = await _make_server_row(db, name="Off Tools", enabled=False)
        agent3 = await _make_agent(db, mcp_ids=[off_server.id])
        assert await _mcp_schemas(db, agent3) == []

        # Another tenant's server id is invisible to this user.
        foreign = await _make_server_row(db, name="Foreign Tools", user_id=777)
        agent4 = await _make_agent(db, mcp_ids=[foreign.id])
        assert await _mcp_schemas(db, agent4) == []

    _run(scenario(db_session))


def test_bridge_execution_routes_to_server(monkeypatch, db_session):
    fake = FakeMCP(call_text="issue #12 created")
    use_fake_server(monkeypatch, fake)

    async def scenario(db):
        from app.services.agent_runner import _execute_mcp_call

        await _make_server_row(db, user_id=41)
        ctx = ToolContext(db=db, user_id=41, agent_id=1)

        out = await _execute_mcp_call("mcp__repo_tools__create_issue", {"title": "hi"}, ctx)
        assert out["status"] == "success"
        assert out["result"] == "issue #12 created"
        assert fake.last_arguments == {"title": "hi"}

        # Unknown slug → error, never another tenant's server.
        out = await _execute_mcp_call("mcp__ghost__create_issue", {}, ctx)
        assert "error" in out

        # Malformed name → error.
        out = await _execute_mcp_call("mcp__broken", {}, ctx)
        assert "Malformed" in out["error"]

    _run(scenario(db_session))
