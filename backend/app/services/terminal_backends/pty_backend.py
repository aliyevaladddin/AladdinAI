# NOTICE: This file is protected under RCF-PL
"""PtyBackend — Python PTY fallback for local terminals.

Used when the aladdin-term C daemon binary/socket is unavailable
(e.g. devcontainers or prod images without the prebuilt binary).
Runs /bin/bash on a fresh PTY and adapts fd I/O to the uniform
TerminalBackend interface.
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


class PtyBackend(TerminalBackend):
    """Local /bin/bash on a freshly opened PTY."""

    name = "pty"

    def __init__(self, shell: str = "/bin/bash"):
        self._shell = shell
        self._master_fd: int | None = None
        self._proc: asyncio.subprocess.Process | None = None

    async def open(self) -> None:
        master_fd, slave_fd = pty.openpty()
        env = dict(os.environ)
        env["TERM"] = "xterm-256color"
        env["COLORTERM"] = "truecolor"

        self._proc = await asyncio.create_subprocess_exec(
            self._shell,
            env=env,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            start_new_session=True,
        )
        os.close(slave_fd)
        self._master_fd = master_fd
        log.info("Terminal backend: python PTY (%s, pid=%s)", self._shell, self._proc.pid)

    async def read(self) -> str:
        if self._master_fd is None:
            raise EOFError("pty not open")
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(None, os.read, self._master_fd, _READ_CHUNK)
        if not data:
            raise EOFError("pty EOF")
        return data.decode("utf-8", errors="replace")

    async def write(self, data: str) -> None:
        if self._master_fd is None:
            raise EOFError("pty not open")
        os.write(self._master_fd, data.encode("utf-8"))

    async def resize(self, cols: int, rows: int) -> None:
        if self._master_fd is None:
            return
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(self._master_fd, termios.TIOCSWINSZ, winsize)
        log.debug("Terminal backend: PTY resize %sx%s", cols, rows)

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
            except Exception:  # pragma: no cover - best effort
                pass
            self._proc = None
