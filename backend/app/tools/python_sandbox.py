# NOTICE: This file is protected under RCF-PL
"""Python Sandbox Execution Tool for AladdinAI.

Executes Python scripts safely in a subprocess and captures standard output,
errors, and return codes.
"""
import asyncio
import logging
import os
import sys
import tempfile
import uuid

from app.tools.base import ToolContext, tool

log = logging.getLogger(__name__)


# [RCF:PROTECTED]
@tool(
    name="run_python_code",
    description=(
        "Execute Python 3 code in an isolated subprocess environment and return stdout/stderr. "
        "Use this for data processing, calculations, table formatting, and script testing."
    ),
    parameters={
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Valid Python 3 code to execute.",
            },
            "timeout_seconds": {
                "type": "integer",
                "default": 15,
                "description": "Maximum execution time in seconds (max 30).",
            },
        },
        "required": ["code"],
    },
)
# [RCF:PROTECTED]
async def run_python_code(
    ctx: ToolContext,
    code: str,
    timeout_seconds: int = 15,
) -> dict:
    if not code or not code.strip():
        return {"status": "error", "message": "No Python code provided."}

    timeout = max(1, min(30, int(timeout_seconds)))

    # 1. Preferred: run inside the agent's Docker sandbox against /workspace.
    from app.services import agent_sandbox

    try:
        container_id = await agent_sandbox.ensure_sandbox(ctx.user_id, ctx.agent_id)
    except Exception:
        container_id = None

    if container_id:
        script = f".aladdin_run_{uuid.uuid4().hex}.py"
        try:
            await agent_sandbox.write_file(container_id, f"{agent_sandbox.WORKDIR}/{script}", code)
            res = await agent_sandbox.exec_in_sandbox(
                container_id,
                f"python {agent_sandbox.quote(script)}",
                timeout=float(timeout),
            )
            if res.timed_out:
                return {"status": "timeout", "message": res.stderr}
            return {
                "status": "success" if res.exit_code == 0 else "execution_failed",
                "exit_code": res.exit_code,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "location": "sandbox",
            }
        except Exception as e:
            log.warning("sandbox python exec failed, host fallback: %s", e)

    # 2. Fallback: host subprocess under rlimits (no docker daemon available).
    # Create temporary script file
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    # Apply the same rlimits the terminal tool uses (CPU/mem/nproc/fsize) so the
    # host fallback isn't unbounded.
    from app.tools.terminal_tools import set_rlimits

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            tmp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=set_rlimits,
        )

        try:
            stdout_data, stderr_data = await asyncio.wait_for(
                proc.communicate(), timeout=float(timeout)
            )
            stdout_str = stdout_data.decode("utf-8", errors="replace")
            stderr_str = stderr_data.decode("utf-8", errors="replace")

            return {
                "status": "success" if proc.returncode == 0 else "execution_failed",
                "exit_code": proc.returncode,
                "stdout": stdout_str,
                "stderr": stderr_str,
            }
        except asyncio.TimeoutError:
            try:
                proc.kill()
                await proc.wait()  # Reap the process to avoid zombie processes
            except Exception:
                pass
            return {
                "status": "timeout",
                "message": f"Execution timed out after {timeout} seconds.",
            }
    except Exception as e:
        log.exception("run_python_code execution error")
        return {"status": "error", "message": str(e)}
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
