# NOTICE: This file is protected under RCF-PL
"""IdeBackend — launches the aladdin-ide C editor (wrt-edit) on a PTY.

The C WRT editor (``backend/native/wrt/wrt-edit``) is a full-screen,
raw-mode terminal application. It must run on a real PTY so that:
  - terminal escape sequences render correctly in xterm.js
  - the editor receives raw keystrokes (arrows, Ctrl+letter combos)
  - resize works via TIOCSWINSZ

This backend mirrors :class:`PtyBackend` but execs ``wrt-edit`` with an
optional ``file`` argument so the editor opens the requested document
on startup.
"""
import asyncio
import fcntl
import logging
import os
import pty
import struct
import termios

from app.services.terminal_backends.base import TerminalBackend

log = logging.getLogger(__name__)

_READ_CHUNK = 4096

# Resolved at import time; overridable via env for tests.
_NATIVE_DIR = os.environ.get(
    "ALADDIN_NATIVE_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "native"),
)
_IDE_BINARY = os.path.join(_NATIVE_DIR, "wrt", "wrt-edit")


async def _resolve_ide_binary() -> str:
    """Locate the compiled wrt-edit binary."""
    global _IDE_BINARY
    if os.path.exists(_IDE_BINARY) and os.access(_IDE_BINARY, os.X_OK):
        return _IDE_BINARY
    # Fallback: try building it via the wrt Makefile.
    wrt_dir = os.path.join(_NATIVE_DIR, "wrt")
    if os.path.exists(os.path.join(wrt_dir, "Makefile")):
        log.info("Building wrt-edit binary from C sources in %s", wrt_dir)
        proc = await asyncio.create_subprocess_exec(
            "make", "-C", wrt_dir, "wrt-edit",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode == 0 and os.path.exists(_IDE_BINARY):
            _IDE_BINARY = os.path.join(wrt_dir, "wrt-edit")
            return _IDE_BINARY
        log.warning("Failed to build wrt-edit: %s", stderr.decode("utf-8", errors="replace"))
    raise FileNotFoundError(f"wrt-edit binary not found at {_IDE_BINARY}")


class IdeBackend(TerminalBackend):
    """PTY backend that runs the C-WRT IDE (``wrt-edit``) with a file argument."""

    name = "ide"

    def __init__(self, file_path: str | None = None, shell_env: dict | None = None):
        self._file_path = file_path
        self._shell_env = shell_env
        self._master_fd: int | None = None
        self._proc: asyncio.subprocess.Process | None = None

    async def open(self) -> None:
        binary = await _resolve_ide_binary()
        master_fd, slave_fd = pty.openpty()

        env = dict(os.environ)
        env["TERM"] = "xterm-256color"
        env["COLORTERM"] = "truecolor"
        if self._shell_env:
            env.update(self._shell_env)

        argv = [binary]
        if self._file_path:
            argv.append(self._file_path)

        self._proc = await asyncio.create_subprocess_exec(
            *argv,
            env=env,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            start_new_session=True,
        )
        os.close(slave_fd)
        self._master_fd = master_fd
        log.info("IDE terminal backend: wrt-edit pid=%s file=%s", self._proc.pid, self._file_path or "(none)")

    async def read(self) -> str:
        if self._master_fd is None:
            raise EOFError("ide backend not open")
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(None, os.read, self._master_fd, _READ_CHUNK)
        if not data:
            raise EOFError("ide backend EOF")
        decoded = data.decode("utf-8", errors="replace")
        log.debug("IDE backend read: %r (len=%d)", decoded, len(decoded))
        return decoded

    async def write(self, data: str) -> None:
        if self._master_fd is None:
            raise EOFError("ide backend not open")
        log.debug("IDE backend write: %r (len=%d)", data, len(data))
        os.write(self._master_fd, data.encode("utf-8"))

    async def resize(self, cols: int, rows: int) -> None:
        if self._master_fd is None:
            return
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(self._master_fd, termios.TIOCSWINSZ, winsize)
        log.debug("IDE backend resize %sx%s", cols, rows)

    async def close(self) -> None:
        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except Exception:  # pragma: no cover - best effort
                pass
            self._master_fd = None
        if self._proc is not None and self._proc.returncode is None:
            try:
                self._proc.terminate()
                await asyncio.wait_for(self._proc.wait(), timeout=2.0)
            except (asyncio.TimeoutError, Exception):  # pragma: no cover
                try:
                    self._proc.kill()
                except Exception:  # pragma: no cover - best effort
                    pass
            self._proc = None


async def try_open_ide(file_path: str | None = None) -> tuple[TerminalBackend, str]:
    """Open the aladdin-ide (wrt-edit) backend.

    Returns ``(backend, name)``.  Raises only on hard failure.
    """
    backend = IdeBackend(file_path=file_path)
    await backend.open()
    return backend, IdeBackend.name
