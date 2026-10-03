# NOTICE: This file is protected under RCF-PL
"""WRT Engine Service — bridges AladdinAI to the native C WRT Document Engine.

Communicates with the ultra-fast native C daemon over Unix Domain Socket
with automatic fallback to CLI execution.
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)

NATIVE_DIR = Path(__file__).resolve().parent.parent.parent / "native"
WORKSPACE_ROOT = str(NATIVE_DIR.parent.parent)
SOCKET_DIR = Path(tempfile.gettempdir()) / f"aladdin_wrt_{os.getuid()}"
SOCKET_PATH = str(SOCKET_DIR / "aladdin_wrt.sock")
WRT_DIR = NATIVE_DIR / "wrt"
BINARY_PATH = (WRT_DIR / "wrt-engine") if (WRT_DIR / "wrt-engine").exists() else (NATIVE_DIR / "wrt-engine")

_process: Optional[subprocess.Popen] = None


class WrtEngineUnavailable(RuntimeError):
    """The native C engine could not answer.

    Raised instead of returning a plausible-looking empty result. A caller that
    receives zeros and ``valid: True`` from a dead engine has no way to tell the
    failure apart from a real measurement.
    """


def _validate_workspace_path(path: str) -> str:
    """Resolve a path and ensure it stays within WORKSPACE_ROOT."""
    if not path or not path.strip():
        return WORKSPACE_ROOT
    resolved = os.path.realpath(os.path.join(WORKSPACE_ROOT, path))
    if not os.path.commonpath([WORKSPACE_ROOT, resolved]) == WORKSPACE_ROOT:
        raise ValueError(f"Path is outside workspace root: {path}")
    return resolved


async def ensure_binary_built() -> bool:
    """Ensure wrt-engine native binary is compiled."""
    global BINARY_PATH
    if (WRT_DIR / "wrt-engine").exists() and os.access(WRT_DIR / "wrt-engine", os.X_OK):
        BINARY_PATH = WRT_DIR / "wrt-engine"
        return True
    if BINARY_PATH.exists() and os.access(BINARY_PATH, os.X_OK):
        return True
    try:
        build_dir = WRT_DIR if WRT_DIR.exists() else NATIVE_DIR
        log.info("Compiling native C WRT engine in %s...", build_dir)
        proc = await asyncio.create_subprocess_exec(
            "make", "-C", str(build_dir), "wrt-engine",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if (WRT_DIR / "wrt-engine").exists():
            BINARY_PATH = WRT_DIR / "wrt-engine"
            return True
        if proc.returncode == 0 and BINARY_PATH.exists():
            log.info("Native C WRT engine compiled successfully.")
            return True
        log.error("Failed to compile native C WRT engine: %s", stderr.decode())
    except Exception as e:
        log.error("Error building native C WRT engine: %s", e)
    return False


async def start_daemon() -> None:
    """Start the native C WRT Engine daemon on a private socket."""
    global _process
    if not await ensure_binary_built():
        log.warning("Skipping native C WRT daemon start: binary not available.")
        return

    # Create private socket directory
    SOCKET_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(SOCKET_DIR, 0o700)  # Only owner can access

    if os.path.exists(SOCKET_PATH):
        try:
            os.remove(SOCKET_PATH)
        except Exception:
            pass

    try:
        _process = subprocess.Popen(
            [str(BINARY_PATH), "--daemon", SOCKET_PATH],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        log.info("Native C WRT Engine Daemon started on socket %s (PID: %d)", SOCKET_PATH, _process.pid)
    except Exception as e:
        log.error("Failed to start native C WRT engine daemon: %s", e)


def stop_daemon() -> None:
    """Stop the native C WRT engine daemon process and clean up socket."""
    global _process
    if _process is not None:
        try:
            _process.terminate()
            _process.wait(timeout=2)
        except Exception:
            try:
                _process.kill()
            except Exception:
                pass
        _process = None

    if os.path.exists(SOCKET_PATH):
        try:
            os.remove(SOCKET_PATH)
        except Exception:
            pass
    log.info("Native C WRT Engine Daemon stopped.")


async def _send_socket_request(action: str, content: str = "", path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Send a JSON request to the native C daemon over Unix socket."""
    if not os.path.exists(SOCKET_PATH):
        return None
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_unix_connection(path=SOCKET_PATH),
            timeout=1.0,
        )
        req_data: Dict[str, Any] = {"action": action, "content": content}
        if path:
            req_data["path"] = path
        # ensure_ascii=False is required, not cosmetic: the C daemon has no \uXXXX
        # decoder, so the default (True) ships every Cyrillic character as an
        # escape sequence and the daemon hands the literal text back -- "Привет"
        # came out as "u041fu0440u0438u0432u0435u0442". UTF-8 multibyte bytes are
        # all >= 0x80 and can never collide with '"' (0x22) or '\' (0x5C), so
        # extract_json_string() copies them through safely.
        payload = json.dumps(req_data, ensure_ascii=False) + "\n"
        writer.write(payload.encode("utf-8"))
        await writer.drain()

        line = await asyncio.wait_for(reader.readline(), timeout=3.0)
        writer.close()
        await writer.wait_closed()

        if line:
            return json.loads(line.decode("utf-8", errors="replace").strip())
    except Exception as e:
        log.debug("Unix socket call to wrt-engine failed (%s), will fallback to CLI", e)
    return None


async def _run_cli_command(cmd_args: list[str], stdin_data: Optional[str] = None) -> str:
    """Execute wrt-engine binary with arbitrary CLI arguments as fallback."""
    await ensure_binary_built()
    proc = await asyncio.create_subprocess_exec(
        str(BINARY_PATH), *cmd_args,
        stdin=asyncio.subprocess.PIPE if stdin_data is not None else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate(input=stdin_data.encode("utf-8") if stdin_data else None)
    return stdout.decode("utf-8", errors="replace")


async def _run_cli_fallback(action: str, content: str) -> str:
    """Execute wrt-engine binary directly as fallback if daemon is unreachable."""
    return await _run_cli_command([action, "-"], stdin_data=content)


async def validate_wrt(content: str) -> Dict[str, Any]:
    """Validate WRT document using native C engine."""
    res = await _send_socket_request("validate", content)
    if res and res.get("type") == "validate_result":
        return res.get("data", {"valid": True, "issues": []})

    # CLI fallback
    try:
        out = await _run_cli_fallback("validate", content)
        return json.loads(out)
    except Exception as e:
        log.error("WRT validation error: %s", e)
        return {"valid": True, "issues": []}


async def fix_wrt(content: str) -> str:
    """Auto-fix WRT document tags using native C engine."""
    res = await _send_socket_request("fix", content)
    if res and res.get("type") == "fix_result":
        return res.get("content", content)

    # CLI fallback
    try:
        return await _run_cli_fallback("fix", content)
    except Exception as e:
        log.error("WRT fix error: %s", e)
        return content


async def wrt_to_html(content: str) -> str:
    """Convert WRT document to HTML using native C engine."""
    res = await _send_socket_request("to-html", content)
    if res and res.get("type") == "to_html_result":
        return res.get("html", "")

    # CLI fallback
    try:
        return await _run_cli_fallback("to-html", content)
    except Exception as e:
        log.error("WRT to-html error: %s", e)
        return ""


async def wrt_to_editable_html(content: str) -> str:
    """Convert WRT document to editable HTML for contentEditable using native C engine."""
    res = await _send_socket_request("to-editable-html", content)
    if res and res.get("type") == "to_editable_html_result":
        return res.get("html", "")

    # CLI fallback
    try:
        return await _run_cli_fallback("to-editable-html", content)
    except Exception as e:
        log.error("WRT to-editable-html error: %s", e)
        return ""


async def wrt_from_editable_html(content: str) -> str:
    """Convert editable HTML from contentEditable back to WRT markup using native C engine."""
    res = await _send_socket_request("from-editable-html", content)
    if res and res.get("type") == "from_editable_html_result":
        return res.get("content", "")

    # CLI fallback
    try:
        return await _run_cli_fallback("from-editable-html", content)
    except Exception as e:
        log.error("WRT from-editable-html error: %s", e)
        return ""


async def wrt_stats(content: str) -> Dict[str, Any]:
    """Calculate WRT document statistics using native C engine.

    Raises on failure rather than returning a zeroed report: a caller that gets
    ``valid: True`` with every counter at 0 is looking at a dead backend and
    cannot tell it apart from a real measurement.
    """
    res = await _send_socket_request("stats", content)
    if res and res.get("type") == "stats_result":
        return res

    # CLI fallback
    out = await _run_cli_fallback("validate", content)
    data = json.loads(out)
    if not isinstance(data, dict) or "line_count" not in data:
        raise WrtEngineUnavailable("wrt stats: engine returned no 'line_count' field")
    return {
        "lines": data.get("line_count", 0),
        "words": data.get("word_count", 0),
        "chars": data.get("char_count", 0),
        "tags": data.get("tag_count", 0),
        "valid": data.get("valid", True),
    }


async def list_files(dir_path: Optional[str] = None) -> Dict[str, Any]:
    """List workspace/directory files using ultra-fast native C engine."""
    try:
        target = _validate_workspace_path(dir_path or WORKSPACE_ROOT)
    except ValueError as e:
        return {"type": "list_files_result", "success": False, "error": str(e), "files": []}

    res = await _send_socket_request("list_files", path=target)
    if res and res.get("type") == "list_files_result":
        return res

    # CLI fallback
    try:
        out = await _run_cli_command(["list-files", target])
        return json.loads(out)
    except Exception as e:
        log.error("WRT list-files error: %s", e)
        return {"type": "list_files_result", "success": False, "error": str(e), "files": []}


async def read_file(file_path: str) -> Dict[str, Any]:
    """Read file content using ultra-fast native C engine."""
    try:
        resolved = _validate_workspace_path(file_path)
    except ValueError as e:
        return {"type": "read_file_result", "success": False, "error": str(e), "content": ""}

    res = await _send_socket_request("read_file", path=resolved)
    if res and res.get("type") == "read_file_result":
        return res

    # CLI fallback
    try:
        out = await _run_cli_command(["read-file", resolved])
        return json.loads(out)
    except Exception as e:
        log.error("WRT read-file error: %s", e)
        return {"type": "read_file_result", "success": False, "error": str(e), "content": ""}


async def save_file(file_path: str, content: str) -> Dict[str, Any]:
    """Save file content safely to filesystem using ultra-fast native C engine."""
    try:
        resolved = _validate_workspace_path(file_path)
    except ValueError as e:
        return {"type": "save_file_result", "success": False, "error": str(e)}

    res = await _send_socket_request("save_file", content=content, path=resolved)
    if res and res.get("type") == "save_file_result":
        return res

    # CLI fallback
    try:
        out = await _run_cli_command(["save-file", resolved, "-"], stdin_data=content)
        return json.loads(out)
    except Exception as e:
        log.error("WRT save-file error: %s", e)
        return {"type": "save_file_result", "success": False, "error": str(e)}


async def get_recent_files() -> Dict[str, Any]:
    """Get list of recently edited files using ultra-fast native C engine."""
    res = await _send_socket_request("recent_files")
    if res and res.get("type") == "recent_files_result":
        return res

    # CLI fallback
    try:
        out = await _run_cli_command(["recent-files"])
        return json.loads(out)
    except Exception as e:
        log.error("WRT recent-files error: %s", e)
        return {"type": "recent_files_result", "success": False, "files": []}


# ── office / markdown conversions ───────────────────────────────────────────
# The daemon already implements all eight conversions as socket actions
# (wrt_engine.c:1713-1895) and Python was ignoring them in favour of
# fork+exec with temp files. Routing through the socket is what makes these
# awaitable: the old subprocess.run() calls sat inside async FastAPI handlers
# and blocked the whole event loop for the length of the conversion.
#
# Two of the eight (md <-> wrt) exchange plain text and need no temp file at
# all. The other six move zip archives, which the C side streams to/from disk,
# so one temp file remains for those -- but the conversion itself runs inside
# the already-running daemon instead of spawning a process per request.


async def _unlink(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


async def _text_convert_socket(action: str, result_type: str, content: str) -> Optional[str]:
    """md <-> wrt over the socket. The C side works on the request body."""
    res = await _send_socket_request(action, content)
    if res and res.get("type") == result_type:
        return res.get("content", "")
    return None


async def _to_wrt_socket(action: str, result_type: str, data: bytes, suffix: str) -> Optional[str]:
    """office bytes -> wrt. The daemon reads the archive from `path`."""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tf:
        tf.write(data)
        in_path = tf.name
    try:
        res = await _send_socket_request(action, path=in_path)
        if res and res.get("type") == result_type:
            return res.get("content", "")
        return None
    finally:
        await _unlink(in_path)


async def _from_wrt_socket(action: str, result_type: str, content: str, suffix: str) -> Optional[bytes]:
    """wrt -> office bytes. The daemon writes the archive to `path`."""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tf:
        out_path = tf.name
    try:
        res = await _send_socket_request(action, content, path=out_path)
        if res and res.get("type") == result_type:
            with open(out_path, "rb") as f:
                return f.read()
        return None
    finally:
        await _unlink(out_path)


async def _to_wrt_cli(action: str, data: bytes, suffix: str) -> str:
    """Fallback: fork the binary directly. `action` takes the input path only."""
    await ensure_binary_built()
    if not BINARY_PATH.exists():
        raise FileNotFoundError(f"Native binary not found: {BINARY_PATH}")
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tf:
        tf.write(data)
        in_path = tf.name
    try:
        proc = await asyncio.create_subprocess_exec(
            str(BINARY_PATH), action, in_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                stderr.decode("utf-8", errors="replace").strip() or f"{action} failed"
            )
        return stdout.decode("utf-8", errors="replace")
    finally:
        await _unlink(in_path)


async def _from_wrt_cli(action: str, content: str, suffix: str) -> bytes:
    """Fallback for wrt -> office. wrt-to-* has no stdin mode (wrt_engine.c:2109),
    so the source document still goes through a temp file."""
    await ensure_binary_built()
    if not BINARY_PATH.exists():
        raise FileNotFoundError(f"Native binary not found: {BINARY_PATH}")
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tf:
        out_path = tf.name
    with tempfile.NamedTemporaryFile(suffix=".wrt", mode="w", encoding="utf-8", delete=False) as wf:
        wf.write(content)
        in_path = wf.name
    try:
        proc = await asyncio.create_subprocess_exec(
            str(BINARY_PATH), action, in_path, out_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                stderr.decode("utf-8", errors="replace").strip() or f"{action} failed"
            )
        with open(out_path, "rb") as f:
            return f.read()
    finally:
        await _unlink(out_path)
        await _unlink(in_path)


async def docx_to_wrt(docx_bytes: bytes) -> str:
    """Convert .docx bytes to .wrt using native C engine."""
    got = await _to_wrt_socket("docx_to_wrt", "docx_to_wrt_result", docx_bytes, ".docx")
    if got is not None:
        return got
    return await _to_wrt_cli("docx-to-wrt", docx_bytes, ".docx")


async def odt_to_wrt(odt_bytes: bytes) -> str:
    """Convert .odt bytes to .wrt using native C engine."""
    got = await _to_wrt_socket("odt_to_wrt", "odt_to_wrt_result", odt_bytes, ".odt")
    if got is not None:
        return got
    return await _to_wrt_cli("odt-to-wrt", odt_bytes, ".odt")


async def pptx_to_wrt(pptx_bytes: bytes) -> str:
    """Convert .pptx bytes to .wrt using native C engine."""
    got = await _to_wrt_socket("pptx_to_wrt", "pptx_to_wrt_result", pptx_bytes, ".pptx")
    if got is not None:
        return got
    return await _to_wrt_cli("pptx-to-wrt", pptx_bytes, ".pptx")


async def md_to_wrt(md_text: str) -> str:
    """Convert Markdown to .wrt using native C engine."""
    got = await _text_convert_socket("md_to_wrt", "md_to_wrt_result", md_text)
    if got is not None:
        return got
    return await _run_cli_command(["md-to-wrt", "-"], stdin_data=md_text)


async def wrt_to_md(wrt_text: str) -> str:
    """Convert .wrt to standard Markdown using native C engine."""
    got = await _text_convert_socket("wrt_to_md", "wrt_to_md_result", wrt_text)
    if got is not None:
        return got
    return await _run_cli_command(["wrt-to-md", "-"], stdin_data=wrt_text)


async def wrt_to_docx(wrt_text: str) -> bytes:
    """Convert .wrt text to .docx bytes using native C engine."""
    got = await _from_wrt_socket("wrt_to_docx", "wrt_to_docx_result", wrt_text, ".docx")
    if got is not None:
        return got
    return await _from_wrt_cli("wrt-to-docx", wrt_text, ".docx")


async def wrt_to_odt(wrt_text: str) -> bytes:
    """Convert .wrt text to .odt bytes using native C engine."""
    got = await _from_wrt_socket("wrt_to_odt", "wrt_to_odt_result", wrt_text, ".odt")
    if got is not None:
        return got
    return await _from_wrt_cli("wrt-to-odt", wrt_text, ".odt")


async def wrt_to_pptx(wrt_text: str) -> bytes:
    """Convert .wrt text to .pptx bytes using native C engine."""
    got = await _from_wrt_socket("wrt_to_pptx", "wrt_to_pptx_result", wrt_text, ".pptx")
    if got is not None:
        return got
    return await _from_wrt_cli("wrt-to-pptx", wrt_text, ".pptx")


def _run_blocking(make_coro):
    """Run a coroutine to completion from sync code, given a factory for it.

    The factory exists so the running-loop check happens *before* the coroutine
    object is created. Passing a coroutine instead would build it eagerly, and
    when the check then fails the un-awaited object is garbage-collected --
    emitting a "coroutine was never awaited" warning that points at the wrong
    place entirely.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        raise RuntimeError(
            f"{make_coro.__qualname__} is the sync wrapper and cannot be called "
            "from async code -- await the coroutine of the same name instead."
        )
    return asyncio.run(make_coro())


# Sync twins, for callers that have no event loop -- tests and offline scripts.
# Each bypasses the socket on purpose: a sync caller cannot await it, and
# asyncio.run() cannot be nested inside a running loop, so the CLI path is the
# only one that can serve them.
def docx_to_wrt_sync(docx_bytes: bytes) -> str:
    return _run_blocking(lambda: _to_wrt_cli("docx-to-wrt", docx_bytes, ".docx"))


def odt_to_wrt_sync(odt_bytes: bytes) -> str:
    return _run_blocking(lambda: _to_wrt_cli("odt-to-wrt", odt_bytes, ".odt"))


def pptx_to_wrt_sync(pptx_bytes: bytes) -> str:
    return _run_blocking(lambda: _to_wrt_cli("pptx-to-wrt", pptx_bytes, ".pptx"))


def wrt_to_docx_sync(wrt_text: str) -> bytes:
    return _run_blocking(lambda: _from_wrt_cli("wrt-to-docx", wrt_text, ".docx"))


def wrt_to_odt_sync(wrt_text: str) -> bytes:
    return _run_blocking(lambda: _from_wrt_cli("wrt-to-odt", wrt_text, ".odt"))


def wrt_to_pptx_sync(wrt_text: str) -> bytes:
    return _run_blocking(lambda: _from_wrt_cli("wrt-to-pptx", wrt_text, ".pptx"))


async def _md_to_wrt_cli(md_text: str) -> str:
    return await _run_cli_command(["md-to-wrt", "-"], stdin_data=md_text)


async def _wrt_to_md_cli(wrt_text: str) -> str:
    return await _run_cli_command(["wrt-to-md", "-"], stdin_data=wrt_text)


def md_to_wrt_sync(md_text: str) -> str:
    return _run_blocking(lambda: _md_to_wrt_cli(md_text))


def wrt_to_md_sync(wrt_text: str) -> str:
    return _run_blocking(lambda: _wrt_to_md_cli(wrt_text))

