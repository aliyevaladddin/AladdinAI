# NOTICE: This file is protected under RCF-PL
import asyncio
import logging
import re
import resource
import subprocess
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.terminal_approval import (
    STATUS_APPROVED,
    STATUS_EXPIRED,
    STATUS_PENDING,
    STATUS_REJECTED,
    TerminalApproval,
)
from app.tools.base import ToolContext, tool

log = logging.getLogger(__name__)

# How long the agent waits for a human, and how often it re-reads the verdict.
# The wait is a poll rather than an awaited Future because the decision arrives
# in whichever worker served the approve request — possibly not this one. Polling
# Postgres is what makes the gate work across workers at all.
APPROVAL_TIMEOUT_SECONDS = 120.0
APPROVAL_POLL_SECONDS = 1.0

SECRET_PATTERNS = [
    re.compile(r"(?:api[_-]?key|secret|token|password|auth|bearer)[\s:=]+['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?", re.IGNORECASE),
    re.compile(r"eyJ[a-zA-Z0-9_\-]*\.[a-zA-Z0-9_\-]*\.[a-zA-Z0-9_\-]*"), # JWT
]


# [RCF:PROTECTED]
async def find_pending(
    db: AsyncSession, request_id: str, user_id: int
) -> TerminalApproval | None:
    """Return a still-pending request only if `user_id` owns it.

    Scoping the lookup by owner is what stops one user settling a command the
    agent asked somebody else about — the request_id is a bearer token otherwise.
    """
    result = await db.execute(
        select(TerminalApproval).where(
            TerminalApproval.request_id == request_id,
            TerminalApproval.user_id == user_id,
            TerminalApproval.status == STATUS_PENDING,
        )
    )
    return result.scalar_one_or_none()


# [RCF:PROTECTED]
async def latest_pending(db: AsyncSession, user_id: int) -> TerminalApproval | None:
    """Return this user's most recent pending request, or None.

    Used when the UI could not carry the request_id back. It resolves only
    against requests the agent actually raised for this user — never a command
    supplied by the caller.
    """
    result = await db.execute(
        select(TerminalApproval)
        .where(
            TerminalApproval.user_id == user_id,
            TerminalApproval.status == STATUS_PENDING,
        )
        .order_by(TerminalApproval.created_at.desc(), TerminalApproval.id.desc())
        .limit(1)
    )
    return result.scalars().first()


# [RCF:PROTECTED]
async def settle(
    db: AsyncSession, approval: TerminalApproval, *, approved: bool, settled_by: int
) -> str:
    """Record the human verdict. Returns the status actually written.

    Guarded by a conditional UPDATE on `status = pending`: two clicks racing (or
    the same click hitting two workers) means the second one changes no row and
    is reported as already-settled, instead of overwriting a decision.
    """
    from sqlalchemy import update

    new_status = STATUS_APPROVED if approved else STATUS_REJECTED
    result = await db.execute(
        update(TerminalApproval)
        .where(
            TerminalApproval.id == approval.id,
            TerminalApproval.status == STATUS_PENDING,
        )
        .values(
            status=new_status,
            settled_by_user_id=settled_by,
            settled_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()
    if result.rowcount == 0:
        await db.refresh(approval)
        return approval.status
    log.info(
        "Terminal execution request %s [%s]",
        "APPROVED" if approved else "REJECTED",
        approval.request_id,
    )
    return new_status


# [RCF:PROTECTED]
def mask_secrets(text: str) -> str:
    """Mask secrets and tokens in stdout/stderr before returning to LLM context."""
    if not text:
        return text
    masked = text
    for pat in SECRET_PATTERNS:
        masked = pat.sub("[MASKED_SECRET]", masked)
    return masked


def set_rlimits():
    """Apply strict Linux rlimits to child process for CPU, Memory, File size, and Process count."""
    try:
        # Max CPU time: 5 seconds
        resource.setrlimit(resource.RLIMIT_CPU, (5, 10))
        # Max virtual memory: 256MB
        resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 512 * 1024 * 1024))
        # Max processes (prevent fork-bombs): 16
        resource.setrlimit(resource.RLIMIT_NPROC, (16, 32))
        # Max file output size: 10MB
        resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 20 * 1024 * 1024))
    except Exception as e:  # noqa: BLE001
        log.warning("Could not set rlimits: %s", e)


@tool(
    name="execute_terminal_command",
    description="Request execution of a bash/C compilation command with explicit user approval gate.",
    parameters={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The exact shell command or build instruction to run (e.g., 'gcc main.c -o main').",
            },
            "rationale": {
                "type": "string",
                "description": "Short justification explaining why this command is needed.",
            },
        },
        "required": ["command", "rationale"],
    },
)
async def execute_terminal_command(ctx: ToolContext, command: str, rationale: str) -> str:
    """Creates a pending approval request and waits for Aladdin's decision in the UI."""
    from app.database import async_session

    request_id = str(uuid.uuid4())

    # Written in its own session and committed immediately: until this row is
    # visible to other connections, a worker handling the approve cannot find the
    # request, and the poll below would never see a verdict.
    async with async_session() as db:
        db.add(TerminalApproval(
            request_id=request_id,
            user_id=ctx.user_id,
            agent_id=ctx.agent_id,
            command=command,
            rationale=rationale,
            status=STATUS_PENDING,
        ))
        await db.commit()

    # Notify via on_step callback if streaming is active
    on_step = ctx.extra.get("on_step")
    if on_step and callable(on_step):
        try:
            await on_step({
                "type": "approval_required",
                "request_id": request_id,
                "command": command,
                "rationale": rationale,
                "text": f"Terminal Execution Request (request_id: {request_id})\nCommand: `{command}`\nRationale: {rationale}",
            })
        except Exception:  # noqa: BLE001, S110
            pass

    log.info("Terminal execution approval requested [%s]: %s", request_id, command)

    status = await _await_verdict(request_id)

    if status == STATUS_PENDING:
        # Nobody answered. Mark it expired so a stale row cannot later be settled
        # into an approval for a tool call that stopped waiting long ago.
        await _expire(request_id)
        return "Terminal Execution Request timed out waiting for user approval."
    if status != STATUS_APPROVED:
        return "Terminal Execution Request was REJECTED by user."

    return await run_approved_command(command, user_id=ctx.user_id, agent_id=ctx.agent_id)


# [RCF:PROTECTED]
async def _await_verdict(request_id: str) -> str:
    """Poll for this request's verdict; return its status, or `pending` on timeout.

    A fresh session per poll on purpose: an AsyncSession holds a repeatable-read
    snapshot, so reusing one would keep returning the `pending` this call itself
    wrote and never observe the approve committed by another worker.
    """
    from app.database import async_session

    deadline = asyncio.get_running_loop().time() + APPROVAL_TIMEOUT_SECONDS
    while True:
        async with async_session() as db:
            result = await db.execute(
                select(TerminalApproval.status).where(
                    TerminalApproval.request_id == request_id
                )
            )
            status = result.scalar_one_or_none()

        if status is not None and status != STATUS_PENDING:
            return status
        if asyncio.get_running_loop().time() >= deadline:
            return STATUS_PENDING
        await asyncio.sleep(APPROVAL_POLL_SECONDS)


# [RCF:PROTECTED]
async def _expire(request_id: str) -> None:
    """Retire an unanswered request. Only touches rows still pending."""
    from sqlalchemy import update

    from app.database import async_session

    async with async_session() as db:
        await db.execute(
            update(TerminalApproval)
            .where(
                TerminalApproval.request_id == request_id,
                TerminalApproval.status == STATUS_PENDING,
            )
            .values(status=STATUS_EXPIRED, settled_at=datetime.now(timezone.utc))
        )
        await db.commit()


# [RCF:PROTECTED]
async def run_approved_command(
    command: str,
    *,
    user_id: int,
    agent_id: int | None = None,
) -> str:
    """Execute an already-approved command, preferring the agent's Docker sandbox.

    In the sandbox the command runs inside the agent's container against its
    private /workspace volume — never the backend host. When Docker is
    unavailable it falls back to a host subprocess under strict rlimits (the
    original behaviour), so local dev without a daemon still works.
    """
    from app.services import agent_sandbox

    # 1. Preferred path: run inside the agent's isolated sandbox.
    try:
        container_id = await agent_sandbox.ensure_sandbox(user_id, agent_id)
    except Exception:  # noqa: BLE001
        container_id = None

    if container_id:
        res = await agent_sandbox.exec_in_sandbox(container_id, command, timeout=15.0)
        stdout = mask_secrets(res.stdout or "")
        stderr = mask_secrets(res.stderr or "")
        loc = "sandbox"
        return (
            f"Execution Exit Code: {res.exit_code} ({loc})\n"
            f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}"
        )

    # 2. Fallback: host subprocess under rlimits (no docker daemon available).
    #    preexec_fn requires a real thread; run_in_executor avoids blocking the event loop.
    def _host_run():
        return subprocess.run(
            ["bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=15,
            preexec_fn=set_rlimits,
            cwd="/workspaces/AladdinAI",
            check=False,
        )

    try:
        res = await asyncio.get_event_loop().run_in_executor(None, _host_run)
        stdout = mask_secrets(res.stdout or "")
        stderr = mask_secrets(res.stderr or "")
        return (
            f"Execution Exit Code: {res.returncode} (host-fallback)\n"
            f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}"
        )
    except subprocess.TimeoutExpired:
        return "Execution timed out (exceeded 15 seconds limit)."
    except Exception as e:  # noqa: BLE001
        return f"Execution failed: {e!s}"
