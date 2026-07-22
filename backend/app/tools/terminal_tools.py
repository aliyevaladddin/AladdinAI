# NOTICE: This file is protected under RCF-PL
import asyncio
import logging
import os
import re
import resource
import subprocess
import uuid
from typing import Any, Dict

from app.tools.base import tool, ToolContext

log = logging.getLogger(__name__)

# In-memory store for pending approval requests
# Key: request_id, Value: Future or dict with event/data
PENDING_APPROVALS: Dict[str, Dict[str, Any]] = {}

SECRET_PATTERNS = [
    re.compile(r"(?:api[_-]?key|secret|token|password|auth|bearer)[\s:=]+['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?", re.IGNORECASE),
    re.compile(r"eyJ[a-zA-Z0-9_\-]*\.[a-zA-Z0-9_\-]*\.[a-zA-Z0-9_\-]*"), # JWT
]


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
    except Exception as e:
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
    request_id = str(uuid.uuid4())
    loop = asyncio.get_running_loop()
    future = loop.create_future()

    PENDING_APPROVALS[request_id] = {
        "command": command,
        "rationale": rationale,
        "user_id": ctx.user_id,
        "future": future,
    }

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
        except Exception:
            pass

    log.info("Terminal execution approval requested [%s]: %s", request_id, command)

    try:
        # Wait up to 120 seconds for user approval in UI
        approved = await asyncio.wait_for(future, timeout=120.0)
    except asyncio.TimeoutError:
        PENDING_APPROVALS.pop(request_id, None)
        return "Terminal Execution Request timed out waiting for user approval."
    finally:
        PENDING_APPROVALS.pop(request_id, None)

    if not approved:
        return "Terminal Execution Request was REJECTED by user."

    # Execute command safely under rlimit
    try:
        res = subprocess.run(
            ["bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=15,
            preexec_fn=set_rlimits,
            cwd=str(ctx.extra.get("cwd", "/workspaces/AladdinAI")),
        )
        stdout = mask_secrets(res.stdout or "")
        stderr = mask_secrets(res.stderr or "")
        code = res.returncode
        return f"Execution Exit Code: {code}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
    except subprocess.TimeoutExpired:
        return "Execution timed out (exceeded 15 seconds limit)."
    except Exception as e:
        return f"Execution failed: {str(e)}"
