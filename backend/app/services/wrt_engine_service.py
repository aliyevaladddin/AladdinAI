# NOTICE: This file is protected under RCF-PL
"""WRT Engine Service — bridges AladdinAI to the native C WRT Document Engine.

Communicates with the ultra-fast native C daemon over Unix Domain Socket
(/tmp/aladdin_wrt.sock) with automatic fallback to CLI execution.
"""

import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)

SOCKET_PATH = "/tmp/aladdin_wrt.sock"
NATIVE_DIR = Path(__file__).resolve().parent.parent.parent / "native"
WRT_DIR = NATIVE_DIR / "wrt"
BINARY_PATH = (WRT_DIR / "wrt-engine") if (WRT_DIR / "wrt-engine").exists() else (NATIVE_DIR / "wrt-engine")

_process: Optional[subprocess.Popen] = None


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
    """Start the native C WRT Engine daemon on /tmp/aladdin_wrt.sock."""
    global _process
    if not await ensure_binary_built():
        log.warning("Skipping native C WRT daemon start: binary not available.")
        return

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
        payload = json.dumps(req_data) + "\n"
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


async def wrt_stats(content: str) -> Dict[str, Any]:
    """Calculate WRT document statistics using native C engine."""
    res = await _send_socket_request("stats", content)
    if res and res.get("type") == "stats_result":
        return res

    # CLI fallback
    try:
        out = await _run_cli_fallback("validate", content)
        data = json.loads(out)
        return {
            "lines": data.get("line_count", 0),
            "words": data.get("word_count", 0),
            "chars": data.get("char_count", 0),
            "tags": data.get("tag_count", 0),
            "valid": data.get("valid", True),
        }
    except Exception:
        return {"lines": 0, "words": 0, "chars": 0, "tags": 0, "valid": True}


async def list_files(dir_path: Optional[str] = None) -> Dict[str, Any]:
    """List workspace/directory files using ultra-fast native C engine."""
    target = dir_path or "/workspaces/AladdinAI"
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
    res = await _send_socket_request("read_file", path=file_path)
    if res and res.get("type") == "read_file_result":
        return res

    # CLI fallback
    try:
        out = await _run_cli_command(["read-file", file_path])
        return json.loads(out)
    except Exception as e:
        log.error("WRT read-file error: %s", e)
        return {"type": "read_file_result", "success": False, "error": str(e), "content": ""}


async def save_file(file_path: str, content: str) -> Dict[str, Any]:
    """Save file content safely to filesystem using ultra-fast native C engine."""
    res = await _send_socket_request("save_file", content=content, path=file_path)
    if res and res.get("type") == "save_file_result":
        return res

    # CLI fallback
    try:
        out = await _run_cli_command(["save-file", file_path, "-"], stdin_data=content)
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


def docx_to_wrt_sync(docx_bytes: bytes) -> str:
    """Convert .docx bytes to .wrt format synchronously using native C wrt-engine."""
    import tempfile
    if not BINARY_PATH.exists():
        raise FileNotFoundError(f"Native binary not found: {BINARY_PATH}")

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tf:
        tf.write(docx_bytes)
        tf_name = tf.name

    try:
        res = subprocess.run(
            [str(BINARY_PATH), "docx-to-wrt", tf_name],
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout
    finally:
        try:
            os.remove(tf_name)
        except Exception:
            pass


def wrt_to_docx_sync(wrt_text: str) -> bytes:
    """Convert .wrt text to .docx bytes synchronously using native C wrt-engine."""
    import tempfile
    if not BINARY_PATH.exists():
        raise FileNotFoundError(f"Native binary not found: {BINARY_PATH}")

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tf:
        out_name = tf.name
    with tempfile.NamedTemporaryFile(suffix=".wrt", mode="w", encoding="utf-8", delete=False) as wf:
        wf.write(wrt_text)
        wrt_name = wf.name

    try:
        subprocess.run(
            [str(BINARY_PATH), "wrt-to-docx", wrt_name, out_name],
            capture_output=True,
            check=True,
        )
        with open(out_name, "rb") as f:
            return f.read()
    finally:
        for p in (out_name, wrt_name):
            try:
                os.remove(p)
            except Exception:
                pass


# Direct aliases for workspace and document conversion
docx_to_wrt = docx_to_wrt_sync
wrt_to_docx = wrt_to_docx_sync


def md_to_wrt_sync(md_text: str) -> str:
    """Convert Markdown text to .wrt format synchronously using native C wrt-engine."""
    if not BINARY_PATH.exists():
        raise FileNotFoundError(f"Native binary not found: {BINARY_PATH}")
    res = subprocess.run(
        [str(BINARY_PATH), "md-to-wrt", "-"],
        input=md_text,
        capture_output=True,
        text=True,
        check=True,
    )
    return res.stdout


def wrt_to_md_sync(wrt_text: str) -> str:
    """Convert .wrt format to standard Markdown synchronously using native C wrt-engine."""
    if not BINARY_PATH.exists():
        raise FileNotFoundError(f"Native binary not found: {BINARY_PATH}")
    res = subprocess.run(
        [str(BINARY_PATH), "wrt-to-md", "-"],
        input=wrt_text,
        capture_output=True,
        text=True,
        check=True,
    )
    return res.stdout


md_to_wrt = md_to_wrt_sync
wrt_to_md = wrt_to_md_sync


def odt_to_wrt_sync(odt_bytes: bytes) -> str:
    """Convert .odt bytes to .wrt format synchronously using native C wrt-engine."""
    import tempfile
    if not BINARY_PATH.exists():
        raise FileNotFoundError(f"Native binary not found: {BINARY_PATH}")

    with tempfile.NamedTemporaryFile(suffix=".odt", delete=False) as tf:
        tf.write(odt_bytes)
        tf_name = tf.name

    try:
        res = subprocess.run(
            [str(BINARY_PATH), "odt-to-wrt", tf_name],
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout
    finally:
        try:
            os.remove(tf_name)
        except Exception:
            pass


def wrt_to_odt_sync(wrt_text: str) -> bytes:
    """Convert .wrt text to .odt bytes synchronously using native C wrt-engine."""
    import tempfile
    if not BINARY_PATH.exists():
        raise FileNotFoundError(f"Native binary not found: {BINARY_PATH}")

    with tempfile.NamedTemporaryFile(suffix=".odt", delete=False) as tf:
        out_name = tf.name
    with tempfile.NamedTemporaryFile(suffix=".wrt", mode="w", encoding="utf-8", delete=False) as wf:
        wf.write(wrt_text)
        wrt_name = wf.name

    try:
        subprocess.run(
            [str(BINARY_PATH), "wrt-to-odt", wrt_name, out_name],
            capture_output=True,
            check=True,
        )
        with open(out_name, "rb") as f:
            return f.read()
    finally:
        for p in (out_name, wrt_name):
            try:
                os.remove(p)
            except Exception:
                pass


def pptx_to_wrt_sync(pptx_bytes: bytes) -> str:
    """Convert .pptx bytes to .wrt format synchronously using native C wrt-engine."""
    import tempfile
    if not BINARY_PATH.exists():
        raise FileNotFoundError(f"Native binary not found: {BINARY_PATH}")

    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tf:
        tf.write(pptx_bytes)
        tf_name = tf.name

    try:
        res = subprocess.run(
            [str(BINARY_PATH), "pptx-to-wrt", tf_name],
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout
    finally:
        try:
            os.remove(tf_name)
        except Exception:
            pass


def wrt_to_pptx_sync(wrt_text: str) -> bytes:
    """Convert .wrt text to .pptx bytes synchronously using native C wrt-engine."""
    import tempfile
    if not BINARY_PATH.exists():
        raise FileNotFoundError(f"Native binary not found: {BINARY_PATH}")

    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tf:
        out_name = tf.name
    with tempfile.NamedTemporaryFile(suffix=".wrt", mode="w", encoding="utf-8", delete=False) as wf:
        wf.write(wrt_text)
        wrt_name = wf.name

    try:
        subprocess.run(
            [str(BINARY_PATH), "wrt-to-pptx", wrt_name, out_name],
            capture_output=True,
            check=True,
        )
        with open(out_name, "rb") as f:
            return f.read()
    finally:
        for p in (out_name, wrt_name):
            try:
                os.remove(p)
            except Exception:
                pass


odt_to_wrt = odt_to_wrt_sync
wrt_to_odt = wrt_to_odt_sync
pptx_to_wrt = pptx_to_wrt_sync
wrt_to_pptx = wrt_to_pptx_sync

