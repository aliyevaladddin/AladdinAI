# NOTICE: This file is protected under RCF-PL
"""The terminal approval gate must not be a way around itself.

`execute_terminal_command` is the only path to a shell, and the approval
endpoints exist to settle a request the agent already raised. These tests pin
the two properties that make the gate real: it never executes a command handed
to it, and one user cannot settle another user's request.
"""
import asyncio

import pytest

from app.tools.terminal_tools import (
    PENDING_APPROVALS,
    find_pending,
    latest_pending,
)


# [RCF:PROTECTED]
@pytest.fixture(autouse=True)
def clear_pending():
    """Keep the module-level store from leaking between tests."""
    PENDING_APPROVALS.clear()
    yield
    PENDING_APPROVALS.clear()


# [RCF:PROTECTED]
def _register(request_id: str, user_id: int, command: str = "echo hi") -> None:
    """Register a pending request without a future — for the lookup helpers alone."""
    PENDING_APPROVALS[request_id] = {
        "command": command,
        "rationale": "test",
        "user_id": user_id,
        "future": None,
    }


# [RCF:PROTECTED]
def _pending(request_id: str, user_id: int, command: str = "echo hi") -> asyncio.Future:
    """Register a pending request the way the tool does, minus the agent loop.

    The future needs a loop, so this is for tests that go through the endpoints.
    """
    loop = asyncio.new_event_loop()
    future: asyncio.Future = loop.create_future()
    _register(request_id, user_id, command)
    PENDING_APPROVALS[request_id]["future"] = future
    return future


# [RCF:PROTECTED]
def test_body_command_is_not_executed(client, auth_headers):
    """A command in the request body must be ignored, not run.

    This is the regression that matters: the endpoint used to fall back to
    executing `payload.command` when nothing was pending, which turned the gate
    into arbitrary execution for any authenticated user.
    """
    res = client.post(
        "/api/terminal/approval/approve_latest",
        headers=auth_headers,
        json={"command": "echo PWNED"},
    )

    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "no_pending_requests"
    # Nothing ran, so there is no output field carrying command results.
    assert "output" not in body
    assert body.get("command") is None


# [RCF:PROTECTED]
def test_approve_resolves_only_own_request(client, auth_headers, test_user):
    """Approving settles the caller's own pending request."""
    future = _pending("req-own", test_user["user_id"])

    res = client.post(
        "/api/terminal/approval/req-own/approve",
        headers=auth_headers,
    )

    assert res.json()["status"] == "approved"
    assert future.done() and future.result() is True


# [RCF:PROTECTED]
def test_cannot_settle_another_users_request(client, auth_headers, test_user):
    """A request_id belonging to somebody else must not be settleable."""
    other_user_id = test_user["user_id"] + 1000
    future = _pending("req-someone-else", other_user_id)

    approve = client.post(
        "/api/terminal/approval/req-someone-else/approve",
        headers=auth_headers,
    )
    reject = client.post(
        "/api/terminal/approval/req-someone-else/reject",
        headers=auth_headers,
    )

    assert approve.json()["status"] == "not_found_or_expired"
    assert reject.json()["status"] == "not_found_or_expired"
    assert not future.done()


# [RCF:PROTECTED]
def test_latest_ignores_other_users_pending(client, auth_headers, test_user):
    """`approve_latest` resolves the caller's newest request, not the global one."""
    mine = _pending("req-mine", test_user["user_id"])
    theirs = _pending("req-theirs", test_user["user_id"] + 1000)

    res = client.post(
        "/api/terminal/approval/approve_latest",
        headers=auth_headers,
    )

    assert res.json()["request_id"] == "req-mine"
    assert mine.done() and mine.result() is True
    assert not theirs.done()


# [RCF:PROTECTED]
def test_reject_latest_scoped_to_caller(client, auth_headers, test_user):
    """Rejection is scoped the same way approval is."""
    mine = _pending("req-mine", test_user["user_id"])

    res = client.post(
        "/api/terminal/approval/reject_latest",
        headers=auth_headers,
    )

    assert res.json()["status"] == "rejected"
    assert mine.done() and mine.result() is False


# [RCF:PROTECTED]
def test_approval_requires_authentication(client):
    """Without a session there is no owner to scope to, so there is no approval."""
    res = client.post(
        "/api/terminal/approval/approve_latest",
        json={"command": "echo PWNED"},
    )

    assert res.status_code in (401, 403)


# [RCF:PROTECTED]
def test_lookup_helpers_scope_by_owner():
    """The helpers, not the endpoints, are where ownership is enforced."""
    _register("a", 1)
    _register("b", 2)

    assert find_pending("a", 1) is not None
    assert find_pending("a", 2) is None
    assert find_pending("missing", 1) is None

    found = latest_pending(2)
    assert found is not None and found[0] == "b"
    assert latest_pending(3) is None
