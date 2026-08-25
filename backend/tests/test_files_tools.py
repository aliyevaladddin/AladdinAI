# NOTICE: This file is protected under RCF-PL v2.0.3
"""Tests for the file-workspace agent tools (the safe set).

Mirrors test_orders: seed through the HTTP API (same DB the tools use),
then run each tool via ToolContext + execute() as an agent acting for that
user. The contract under test:

  * every tool re-checks space membership of the chatting user,
  * mutations need editor (a viewer gets an error, not a write),
  * every agent action lands in the timeline with actor_type="agent",
  * there is no delete tool — agents cannot remove documents.
"""
import asyncio

from app.tools.base import REGISTRY, ToolContext, execute


# ── helpers ──────────────────────────────────────────────────────────────────


def _register(client) -> dict:
    email = f"tool-{__import__('uuid').uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": "testpassword123", "name": "Tool User"},
    )
    assert r.status_code == 201, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    uid = client.get("/api/auth/me", headers=headers).json()["id"]
    return {"headers": headers, "user_id": uid}


def _space_with_file(client, headers) -> tuple[int, int]:
    space_id = client.post("/api/spaces", json={"name": "S"}, headers=headers).json()["id"]
    file = client.post(
        f"/api/spaces/{space_id}/files/upload",
        files={"file": ("report.txt", b"v1 body", "text/plain")},
        headers=headers,
    ).json()
    return space_id, file["id"]


def _ctx(db_session, user_id: int, agent_id: int = 5) -> ToolContext:
    return ToolContext(db=db_session, user_id=user_id, agent_id=agent_id)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _events(client, headers, file_id) -> list[dict]:
    return client.get(f"/api/files/{file_id}/events", headers=headers).json()


# ── registry shape ───────────────────────────────────────────────────────────


def test_safe_set_registered_no_delete():
    names = {n for n in REGISTRY if n.startswith("files_")}
    assert names == {
        "files_list", "files_read", "files_upload_version", "files_move", "files_rename",
    }


# ── reads ────────────────────────────────────────────────────────────────────


def test_files_list_and_read(client, auth_headers, db_session):
    uid = client.get("/api/auth/me", headers=auth_headers).json()["id"]
    space_id, file_id = _space_with_file(client, auth_headers)

    listed = _run(execute("files_list", {"space_id": space_id}, _ctx(db_session, uid)))
    assert listed["status"] == "success"
    assert [f["id"] for f in listed["files"]] == [file_id]
    assert listed["files"][0]["version_no"] == 1

    read = _run(execute("files_read", {"file_id": file_id}, _ctx(db_session, uid)))
    assert read["status"] == "success"
    assert read["content"] == "v1 body"
    assert read["version_no"] == 1

    # Reading logs like any other download — but marked as the agent's.
    evs = _events(client, auth_headers, file_id)
    downloaded = [e for e in evs if e["event_type"] == "downloaded"]
    assert len(downloaded) == 1
    assert downloaded[0]["actor_type"] == "agent"


def test_files_read_specific_version(client, auth_headers, db_session):
    uid = client.get("/api/auth/me", headers=auth_headers).json()["id"]
    _, file_id = _space_with_file(client, auth_headers)
    client.post(
        f"/api/files/{file_id}/upload_version",
        files={"file": ("report.txt", b"v2 body", "text/plain")},
        headers=auth_headers,
    )

    old = _run(execute("files_read",
                       {"file_id": file_id, "version_no": 1},
                       _ctx(db_session, uid)))
    assert old["content"] == "v1 body"


def test_non_member_gets_error_not_data(client, auth_headers, db_session):
    owner_headers = auth_headers
    outsider = _register(client)
    _, file_id = _space_with_file(client, owner_headers)

    read = _run(execute("files_read", {"file_id": file_id},
                        _ctx(db_session, outsider["user_id"])))
    listed = _run(execute("files_list", {"space_id": 10**9},
                          _ctx(db_session, outsider["user_id"])))
    assert read["status"] == "error"
    assert listed["status"] == "error"


# ── mutations ────────────────────────────────────────────────────────────────


def test_files_upload_version_authored_by_agent(client, auth_headers, db_session):
    uid = client.get("/api/auth/me", headers=auth_headers).json()["id"]
    space_id, file_id = _space_with_file(client, auth_headers)

    out = _run(execute(
        "files_upload_version",
        {"file_id": file_id, "content": "rewritten by agent", "comment": "AI pass"},
        _ctx(db_session, uid, agent_id=7),
    ))
    assert out["status"] == "success", out
    assert out["new_version_no"] == 2

    # The API sees the new content; v1 stays readable (append-only).
    current = client.get(f"/api/files/{file_id}/download", headers=auth_headers)
    v1 = client.get(f"/api/files/{file_id}/download?version=1", headers=auth_headers)
    assert current.content == b"rewritten by agent"
    assert v1.content == b"v1 body"

    versions = client.get(f"/api/files/{file_id}/versions", headers=auth_headers).json()
    v2 = next(v for v in versions if v["version_no"] == 2)
    assert v2["author_type"] == "agent"
    assert v2["agent_run_id"] == 7

    evs = _events(client, auth_headers, file_id)
    added = [e for e in evs if e["event_type"] == "version_added"
             and e["actor_type"] == "agent"]
    assert len(added) == 1
    assert "agent_id" in added[0]["payload"] or added[0].get("payload")


def test_files_move_and_rename_record_agent_events(client, auth_headers, db_session):
    uid = client.get("/api/auth/me", headers=auth_headers).json()["id"]
    space_id, file_id = _space_with_file(client, auth_headers)
    folder_id = client.post(
        f"/api/spaces/{space_id}/folders", json={"name": "F"}, headers=auth_headers,
    ).json()["id"]

    moved = _run(execute("files_move",
                         {"file_id": file_id, "folder_id": folder_id},
                         _ctx(db_session, uid)))
    renamed = _run(execute("files_rename",
                           {"file_id": file_id, "name": "  Q4-report.txt  "},
                           _ctx(db_session, uid)))
    assert moved["status"] == "success" and moved["folder_id"] == folder_id
    assert renamed["status"] == "success" and renamed["name"] == "Q4-report.txt"

    listed = client.get(
        f"/api/spaces/{space_id}/files?folder_id={folder_id}", headers=auth_headers,
    ).json()
    assert [(f["id"], f["name"]) for f in listed] == [(file_id, "Q4-report.txt")]

    types = {e["event_type"]: e for e in _events(client, auth_headers, file_id)}
    assert types["moved"]["actor_type"] == "agent"
    assert types["renamed"]["actor_type"] == "agent"


def test_viewer_cannot_mutate_via_tools(client, db_session):
    alice = _register(client)
    bob = _register(client)
    space_id, file_id = _space_with_file(client, alice["headers"])
    r = client.post(
        f"/api/spaces/{space_id}/members",
        json={"user_id": bob["user_id"], "role": "viewer"},
        headers=alice["headers"],
    )
    assert r.status_code == 201

    bob_ctx = _ctx(db_session, bob["user_id"])
    assert _run(execute("files_upload_version",
                        {"file_id": file_id, "content": "nope"}, bob_ctx))["status"] == "error"
    assert _run(execute("files_move",
                        {"file_id": file_id, "folder_id": None}, bob_ctx))["status"] == "error"
    assert _run(execute("files_rename",
                        {"file_id": file_id, "name": "nope"}, bob_ctx))["status"] == "error"

    # Nothing was written.
    current = client.get(f"/api/files/{file_id}/download", headers=alice["headers"])
    assert current.content == b"v1 body"
