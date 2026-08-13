# NOTICE: This file is protected under RCF-PL
"""The terminal approval gate must not be a way around itself.

`execute_terminal_command` is the only path to a shell, and the approval
endpoints exist to settle a request the agent already raised. These tests pin
the two properties that make the gate real: it never executes a command handed
to it, and one user cannot settle another user's request.

The requests live in Postgres rather than process memory, so they are also
tested for the property that motivated the move: a verdict recorded by one
connection is visible to another (i.e. to another worker), and a request can
only be settled once.
"""
import asyncio

import pytest
from sqlalchemy import delete

from app.models.terminal_approval import (
    STATUS_APPROVED,
    STATUS_EXPIRED,
    STATUS_PENDING,
    STATUS_REJECTED,
    TerminalApproval,
)
from app.tools.terminal_tools import find_pending, latest_pending, settle


# [RCF:PROTECTED]
@pytest.fixture(autouse=True)
def clear_approvals(db_session):
    """Drop rows between tests.

    The schema is created once per session, so committed requests would
    otherwise outlive the test that made them and collide on `request_id`.
    """
    async def _clear():
        await db_session.execute(delete(TerminalApproval))
        await db_session.commit()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_clear())
    yield
    loop.run_until_complete(_clear())


# [RCF:PROTECTED]
@pytest.fixture
def add_pending(db_session):
    """Insert a pending request the way the tool does, minus the agent loop.

    Synchronous because the endpoint tests drive TestClient, which runs its own
    loop; the insert is pushed onto the session's loop the same way the app does.
    """
    def _add(request_id: str, user_id: int, command: str = "echo hi"):
        async def _go():
            row = TerminalApproval(
                request_id=request_id,
                user_id=user_id,
                command=command,
                rationale="test",
                status=STATUS_PENDING,
            )
            db_session.add(row)
            await db_session.commit()
            return row

        return asyncio.get_event_loop().run_until_complete(_go())

    return _add


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
def test_approve_resolves_only_own_request(client, auth_headers, test_user, add_pending):
    """Approving settles the caller's own pending request."""
    add_pending("req-own", test_user["user_id"])

    res = client.post(
        "/api/terminal/approval/req-own/approve",
        headers=auth_headers,
    )

    assert res.json()["status"] == "approved"


# [RCF:PROTECTED]
def test_cannot_settle_another_users_request(client, auth_headers, test_user, add_pending):
    """A request_id belonging to somebody else must not be settleable."""
    other_user_id = test_user["user_id"] + 1000
    row = add_pending("req-someone-else", other_user_id)

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
    # The other user's request is untouched — still awaiting its own owner.
    assert row.status == STATUS_PENDING


# [RCF:PROTECTED]
def test_latest_ignores_other_users_pending(client, auth_headers, test_user, add_pending):
    """`approve_latest` resolves the caller's newest request, not the global one."""
    add_pending("req-theirs", test_user["user_id"] + 1000)
    add_pending("req-mine", test_user["user_id"])

    res = client.post(
        "/api/terminal/approval/approve_latest",
        headers=auth_headers,
    )

    assert res.json()["request_id"] == "req-mine"


# [RCF:PROTECTED]
def test_reject_latest_scoped_to_caller(client, auth_headers, test_user, add_pending):
    """Rejection is scoped the same way approval is."""
    add_pending("req-mine", test_user["user_id"])

    res = client.post(
        "/api/terminal/approval/reject_latest",
        headers=auth_headers,
    )

    assert res.json()["status"] == "rejected"


# [RCF:PROTECTED]
def test_approval_requires_authentication(client):
    """Without a session there is no owner to scope to, so there is no approval."""
    res = client.post(
        "/api/terminal/approval/approve_latest",
        json={"command": "echo PWNED"},
    )

    assert res.status_code in (401, 403)


# [RCF:PROTECTED]
def test_settled_request_cannot_be_settled_again(client, auth_headers, test_user, add_pending):
    """A verdict is final: the second click reports it, it does not overwrite it.

    Two workers can serve two clicks concurrently, so the guard is a conditional
    UPDATE on `status = pending`, not a read-then-write.
    """
    add_pending("req-twice", test_user["user_id"])

    first = client.post("/api/terminal/approval/req-twice/approve", headers=auth_headers)
    second = client.post("/api/terminal/approval/req-twice/reject", headers=auth_headers)

    assert first.json()["status"] == "approved"
    # Already settled, so it is no longer pending and the lookup declines it.
    assert second.json()["status"] == "not_found_or_expired"


# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_lookup_helpers_scope_by_owner(db_session):
    """The helpers, not the endpoints, are where ownership is enforced."""
    db_session.add_all([
        TerminalApproval(request_id="a", user_id=1, command="echo a", status=STATUS_PENDING),
        TerminalApproval(request_id="b", user_id=2, command="echo b", status=STATUS_PENDING),
    ])
    await db_session.commit()

    assert await find_pending(db_session, "a", 1) is not None
    assert await find_pending(db_session, "a", 2) is None
    assert await find_pending(db_session, "missing", 1) is None

    found = await latest_pending(db_session, 2)
    assert found is not None and found.request_id == "b"
    assert await latest_pending(db_session, 3) is None


# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_settled_request_is_no_longer_pending(db_session):
    """Once settled, a request drops out of the pending lookups.

    Without this a stale row could be approved long after the tool call that
    raised it gave up waiting.
    """
    row = TerminalApproval(
        request_id="c", user_id=7, command="echo c", status=STATUS_PENDING
    )
    db_session.add(row)
    await db_session.commit()

    status = await settle(db_session, row, approved=True, settled_by=7)

    assert status == STATUS_APPROVED
    assert await find_pending(db_session, "c", 7) is None
    assert await latest_pending(db_session, 7) is None


# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_settle_is_idempotent_under_race(db_session):
    """The losing side of a race is told the verdict, not allowed to flip it."""
    row = TerminalApproval(
        request_id="d", user_id=8, command="echo d", status=STATUS_PENDING
    )
    db_session.add(row)
    await db_session.commit()

    first = await settle(db_session, row, approved=True, settled_by=8)
    second = await settle(db_session, row, approved=False, settled_by=8)

    assert first == STATUS_APPROVED
    assert second == STATUS_APPROVED  # not flipped to rejected


# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_expired_request_is_not_settleable(db_session):
    """A request that timed out cannot later be turned into an approval."""
    row = TerminalApproval(
        request_id="e", user_id=9, command="echo e", status=STATUS_EXPIRED
    )
    db_session.add(row)
    await db_session.commit()

    assert await find_pending(db_session, "e", 9) is None
    assert await settle(db_session, row, approved=True, settled_by=9) == STATUS_EXPIRED


# [RCF:PROTECTED]
@pytest.mark.asyncio
# [RCF:PROTECTED]
async def test_rejection_is_recorded_with_owner(db_session):
    """The audit trail says who settled it and when."""
    row = TerminalApproval(
        request_id="f", user_id=11, command="rm -rf /", status=STATUS_PENDING
    )
    db_session.add(row)
    await db_session.commit()

    status = await settle(db_session, row, approved=False, settled_by=11)
    await db_session.refresh(row)

    assert status == STATUS_REJECTED
    assert row.settled_by_user_id == 11
    assert row.settled_at is not None
