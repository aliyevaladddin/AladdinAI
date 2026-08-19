# NOTICE: This file is protected under RCF-PL
import asyncio
import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

SOCKET_PATH = "/tmp/aladdin_term.sock"
NATIVE_DIR = Path(__file__).resolve().parent.parent.parent / "native"
BINARY_PATH = NATIVE_DIR / "aladdin-term"

_process: Optional[subprocess.Popen] = None


async def ensure_binary_built() -> bool:
    """Build aladdin-term C binary via make if it does not exist."""
    if BINARY_PATH.exists() and os.access(BINARY_PATH, os.X_OK):
        return True
    try:
        log.info("Compiling native C terminal daemon in %s...", NATIVE_DIR)
        proc = await asyncio.create_subprocess_exec(
            "make", "-C", str(NATIVE_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode == 0 and BINARY_PATH.exists():
            log.info("Native C terminal daemon compiled successfully.")
            return True
        log.error("Failed to compile native C daemon: %s", stderr.decode())
    except Exception as e:
        log.error("Error building native C daemon: %s", e)
    return False


async def start_daemon():
    """Start the native C terminal daemon on /tmp/aladdin_term.sock."""
    global _process
    if not await ensure_binary_built():
        log.warning("Skipping native C daemon start: binary not available.")
        return

    # Clean up stale socket
    if os.path.exists(SOCKET_PATH):
        try:
            os.remove(SOCKET_PATH)
        except Exception:
            pass

    try:
        _process = subprocess.Popen(
            [str(BINARY_PATH), "--socket", SOCKET_PATH],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        log.info("Native C Terminal Daemon started on socket %s (PID: %d)", SOCKET_PATH, _process.pid)
    except Exception as e:
        log.error("Failed to start native C terminal daemon: %s", e)


def stop_daemon():
    """Stop the native C terminal daemon process and clean up socket."""
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
    log.info("Native C Terminal Daemon stopped.")
