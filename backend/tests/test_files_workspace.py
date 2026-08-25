# NOTICE: This file is protected under RCF-PL
"""Tests for the file workspace router: spaces, members, folders, files,
versions (append-only) and the audit timeline."""

import uuid


# ── helpers ─────────────────────────────────────────────────────────────────


def _register(client) -> dict:
    """Register a fresh user, return {'headers', 'user_id'}."""
    email = f"ws-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": "testpassword123", "name": "WS User"},
    )
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    return {"headers": headers, "user_id": me.json()["id"]}


def _create_space(client, headers, name="Workspace") -> dict:
    r = client.post("/api/spaces", json={"name": name}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _upload(client, headers, space_id, content=b"hello", filename="report.txt"):
    r = client.post(
        f"/api/spaces/{space_id}/files/upload",
        files={"file": (filename, content, "text/plain")},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


# ── spaces & isolation ──────────────────────────────────────────────────────


def test_create_space_gives_owner_role(client, auth_headers):
    space = _create_space(client, auth_headers)
    assert space["my_role"] == "owner"
    assert space["name"] == "Workspace"


def test_spaces_are_isolated_between_users(client):
    alice = _register(client)
    bob = _register(client)

    space = _create_space(client, alice["headers"], "Sales")
    mine = client.get("/api/spaces", headers=alice["headers"]).json()
    theirs = client.get("/api/spaces", headers=bob["headers"]).json()

    assert [s["id"] for s in mine] == [space["id"]]
    assert all(s["id"] != space["id"] for s in theirs)

    # Bob is not a member: every surface must refuse him.
    assert client.get(
        f"/api/spaces/{space['id']}/files", headers=bob["headers"]
    ).status_code == 403
    assert client.get(
        f"/api/spaces/{space['id']}/folders", headers=bob["headers"]
    ).status_code == 403


def test_rename_requires_owner(client):
    alice = _register(client)
    bob = _register(client)
    space = _create_space(client, alice["headers"])

    client.post(
        f"/api/spaces/{space['id']}/members",
        json={"user_id": bob["user_id"], "role": "viewer"},
        headers=alice["headers"],
    )
    assert client.patch(
        f"/api/spaces/{space['id']}", json={"name": "Hacked"},
        headers=bob["headers"],
    ).status_code == 403
    assert client.patch(
        f"/api/spaces/{space['id']}", json={"name": "Renamed"},
        headers=alice["headers"],
    ).status_code == 200


# ── upload / download / versions ────────────────────────────────────────────


def test_upload_then_download_roundtrip(client, auth_headers):
    space = _create_space(client, auth_headers)
    file = _upload(client, auth_headers, space["id"], content=b"payload-1")

    assert file["current_version_no"] == 1
    assert file["byte_size"] == len(b"payload-1")

    r = client.get(f"/api/files/{file['id']}/download", headers=auth_headers)
    assert r.status_code == 200
    assert r.content == b"payload-1"


def test_new_version_keeps_old_readable(client, auth_headers):
    space = _create_space(client, auth_headers)
    file = _upload(client, auth_headers, space["id"], content=b"one")

    r = client.post(
        f"/api/files/{file['id']}/upload_version",
        files={"file": ("report.txt", b"two", "text/plain")},
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["version_no"] == 2

    current = client.get(f"/api/files/{file['id']}/download", headers=auth_headers)
    old = client.get(
        f"/api/files/{file['id']}/download?version=1", headers=auth_headers
    )
    assert current.content == b"two"
    assert old.content == b"one"


def test_restore_appends_never_rewrites(client, auth_headers):
    space = _create_space(client, auth_headers)
    file = _upload(client, auth_headers, space["id"], content=b"v1-body")
    client.post(
        f"/api/files/{file['id']}/upload_version",
        files={"file": ("report.txt", b"v2-body", "text/plain")},
        headers=auth_headers,
    )

    r = client.post(
        f"/api/files/{file['id']}/restore",
        json={"version_no": 1},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["version_no"] == 3

    current = client.get(f"/api/files/{file['id']}/download", headers=auth_headers)
    assert current.content == b"v1-body"

    versions = client.get(f"/api/files/{file['id']}/versions", headers=auth_headers)
    nos = [v["version_no"] for v in versions.json()]
    assert nos == [3, 2, 1]  # desc order, nothing rewritten


# ── roles ───────────────────────────────────────────────────────────────────


def _add_member(client, owner_headers, space_id, user_id, role):
    r = client.post(
        f"/api/spaces/{space_id}/members",
        json={"user_id": user_id, "role": role},
        headers=owner_headers,
    )
    assert r.status_code == 201, r.text


def test_viewer_reads_but_cannot_mutate(client):
    alice = _register(client)
    bob = _register(client)
    space = _create_space(client, alice["headers"])
    file = _upload(client, alice["headers"], space["id"])
    _add_member(client, alice["headers"], space["id"], bob["user_id"], "viewer")

    # Reads are allowed…
    assert client.get(
        f"/api/spaces/{space['id']}/files", headers=bob["headers"]
    ).status_code == 200
    assert client.get(
        f"/api/files/{file['id']}/download", headers=bob["headers"]
    ).status_code == 200

    # …mutations are not.
    assert client.post(
        f"/api/files/{file['id']}/upload_version",
        files={"file": ("x.txt", b"x", "text/plain")},
        headers=bob["headers"],
    ).status_code == 403
    assert client.patch(
        f"/api/files/{file['id']}/move", json={"folder_id": None},
        headers=bob["headers"],
    ).status_code == 403
    assert client.delete(
        f"/api/files/{file['id']}", headers=bob["headers"]
    ).status_code == 403
    assert client.post(
        f"/api/spaces/{space['id']}/files/upload",
        files={"file": ("y.txt", b"y", "text/plain")},
        headers=bob["headers"],
    ).status_code == 403


def test_editor_can_upload_version(client):
    alice = _register(client)
    bob = _register(client)
    space = _create_space(client, alice["headers"])
    file = _upload(client, alice["headers"], space["id"])
    _add_member(client, alice["headers"], space["id"], bob["user_id"], "editor")

    r = client.post(
        f"/api/files/{file['id']}/upload_version",
        files={"file": ("report.txt", b"from-bob", "text/plain")},
        headers=bob["headers"],
    )
    assert r.status_code == 201
    # Bob-uploaded version stays readable through Alice's scope boundary.
    current = client.get(f"/api/files/{file['id']}/download", headers=alice["headers"])
    assert current.content == b"from-bob"


def test_outsider_cannot_touch_file(client):
    alice = _register(client)
    outsider = _register(client)
    space = _create_space(client, alice["headers"])
    file = _upload(client, alice["headers"], space["id"])

    assert client.get(
        f"/api/files/{file['id']}/download", headers=outsider["headers"]
    ).status_code == 403
    assert client.get(
        f"/api/files/{file['id']}/versions", headers=outsider["headers"]
    ).status_code == 403
    assert client.get(
        f"/api/files/{file['id']}/events", headers=outsider["headers"]
    ).status_code == 403


def test_last_owner_cannot_be_demoted_or_removed(client):
    alice = _register(client)
    bob = _register(client)
    space = _create_space(client, alice["headers"])

    demote = client.patch(
        f"/api/spaces/{space['id']}/members/{alice['user_id']}",
        json={"role": "viewer"},
        headers=alice["headers"],
    )
    remove = client.delete(
        f"/api/spaces/{space['id']}/members/{alice['user_id']}",
        headers=alice["headers"],
    )
    assert demote.status_code == 400
    assert remove.status_code == 400

    # With a second owner, demotion becomes possible.
    _add_member(client, alice["headers"], space["id"], bob["user_id"], "owner")
    ok = client.patch(
        f"/api/spaces/{space['id']}/members/{alice['user_id']}",
        json={"role": "editor"},
        headers=alice["headers"],
    )
    assert ok.status_code == 200


# ── folders / soft delete ───────────────────────────────────────────────────


def test_move_file_into_folder(client, auth_headers):
    space = _create_space(client, auth_headers)
    folder = client.post(
        f"/api/spaces/{space['id']}/folders",
        json={"name": "Accounting"},
        headers=auth_headers,
    ).json()
    file = _upload(client, auth_headers, space["id"])

    r = client.patch(
        f"/api/files/{file['id']}/move",
        json={"folder_id": folder["id"]},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["folder_id"] == folder["id"]

    listed = client.get(
        f"/api/spaces/{space['id']}/files?folder_id={folder['id']}",
        headers=auth_headers,
    ).json()
    assert [f["id"] for f in listed] == [file["id"]]


def test_soft_deleted_files_disappear_but_history_stays(client, auth_headers):
    space = _create_space(client, auth_headers)
    file = _upload(client, auth_headers, space["id"])

    assert client.delete(
        f"/api/files/{file['id']}", headers=auth_headers
    ).status_code == 204

    listed = client.get(
        f"/api/spaces/{space['id']}/files", headers=auth_headers
    ).json()
    assert listed == []
    assert client.get(
        f"/api/files/{file['id']}/download", headers=auth_headers
    ).status_code == 404

    # The audit trail survives the delete — that is its purpose.
    events = client.get(f"/api/files/{file['id']}/events", headers=auth_headers)
    assert events.status_code == 200
    types = [e["event_type"] for e in events.json()]
    assert "deleted" in types
    assert "created" in types


# ── timeline ────────────────────────────────────────────────────────────────


def test_timeline_records_the_full_story(client, auth_headers):
    space = _create_space(client, auth_headers)
    file = _upload(client, auth_headers, space["id"], content=b"body")
    client.post(
        f"/api/files/{file['id']}/upload_version",
        files={"file": ("report.txt", b"body2", "text/plain")},
        headers=auth_headers,
    )
    client.get(f"/api/files/{file['id']}/download", headers=auth_headers)
    client.post(
        f"/api/files/{file['id']}/restore",
        json={"version_no": 1},
        headers=auth_headers,
    )

    events = client.get(f"/api/files/{file['id']}/events", headers=auth_headers).json()
    types = [e["event_type"] for e in events]
    for expected in ("created", "version_added", "downloaded", "restored"):
        assert expected in types
    assert all(e["actor_type"] == "human" for e in events)


def test_endpoints_require_auth(client):
    assert client.get("/api/spaces").status_code in (401, 403)
    assert client.get("/api/files/1/download").status_code in (401, 403)
