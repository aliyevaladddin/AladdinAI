# NOTICE: This file is protected under RCF-PL
"""SshBackend — terminal over asyncssh to a user's VM connection.

Adapts the asyncssh process channel (stdout/stderr/stdin + terminal size)
to the uniform TerminalBackend interface. Connection credentials are
decrypted from the VMConnection row by the caller-supplied connect factory,
so this module stays free of crypto/DB concerns.
"""
import logging

import asyncssh

from app.services.ssh_known_hosts import resolve_known_hosts
from app.services.terminal_backends.base import TerminalBackend

log = logging.getLogger(__name__)


class SshBackend(TerminalBackend):
    """Interactive shell on a remote host via asyncssh."""

    name = "ssh"

    def __init__(self, conn: asyncssh.SSHClientConnection):
        self._conn = conn
        self._process: asyncssh.SSHProcess | None = None

    async def open(self) -> None:
        self._process = await self._conn.create_process(
            term_type="xterm-256color",
            term_size=(80, 24),
            encoding="utf-8",
        )
        log.info("Terminal backend: ssh shell started")

    async def read(self) -> str:
        if self._process is None:
            raise EOFError("ssh process not open")
        data = await self._process.stdout.read(4096)
        if not data:
            raise EOFError("ssh stdout EOF")
        return data

    async def write(self, data: str) -> None:
        if self._process is None:
            raise EOFError("ssh process not open")
        self._process.stdin.write(data)

    async def resize(self, cols: int, rows: int) -> None:
        if self._process is None:
            return
        self._process.change_terminal_size(cols, rows)
        log.debug("Terminal backend: ssh resize %sx%s", cols, rows)

    async def close(self) -> None:
        if self._process is not None:
            try:
                self._process.terminate()
            except Exception:  # pragma: no cover - best effort
                pass
            self._process = None


async def connect_vm(
    host: str,
    port: int,
    username: str,
    *,
    password: str | None = None,
    private_key: str | None = None,
) -> asyncssh.SSHClientConnection:
    """Open an asyncssh connection with TOFU known-hosts pinning.

    `private_key` is the already-decrypted PEM text (the router decrypts
    `ssh_key_encrypted` before calling us).
    """
    connect_kwargs: dict = {
        "host": host,
        "port": port,
        "username": username,
        "known_hosts": resolve_known_hosts(),
        "connect_timeout": 30,
    }
    if private_key:
        connect_kwargs["client_keys"] = [asyncssh.import_private_key(private_key)]
    elif password:
        connect_kwargs["password"] = password
    return await asyncssh.connect(**connect_kwargs)
