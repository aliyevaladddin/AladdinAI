# NOTICE: This file is protected under RCF-PL
"""Python Sandbox Execution Tool for AladdinAI.

Executes Python scripts safely in a subprocess and captures standard output,
errors, and return codes.
"""
import asyncio
import logging
import sys
import tempfile
import os

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

    # Create temporary script file
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            tmp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
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
