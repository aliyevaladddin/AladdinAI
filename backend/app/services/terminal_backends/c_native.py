# NOTICE: This file is protected under RCF-PL
"""CNativeBackend — first-class backend backed by the aladdin-term C daemon.

The daemon (backend/native/aladdin_term.c) listens on a unix socket,
creates its own PTY and speaks line-delimited JSON:

    inbound  (daemon -> us): {"type":"data","data":"..."} | {"type":"exit"}
    outbound (us -> daemon): {"type":"data","data":"..."} | {"type":"resize",...}

This backend adapts that JSON framing to the uniform TerminalBackend
interface (raw str in/out), so the WS router never knows it is talking to C.
"""
import asyncio
import json
import logging
import os

from app.services.terminal_backends.base import TerminalBackend

log = logging.getLogger(__name__)

SOCKET_PATH = "/tmp/aladdin_term.sock"
_CONNECT_TIMEOUT = 0.4


def is_daemon_available() -> bool:
    """Cheap check used before attempting a connection."""
    return os.path.exists(SOCKET_PATH)


class CNativeBackend(TerminalBackend):
    """Relay terminal I/O through the aladdin-term unix socket."""

    name = "c-native"

    def __init__(self, socket_path: str = SOCKET_PATH):
        self._socket_path = socket_path
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def open(self) -> None:
        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_unix_connection(path=self._socket_path),
            timeout=_CONNECT_TIMEOUT,
        )
        log.info("Terminal backend: connected to native C daemon (%s)", self._socket_path)

    async def read(self) -> str:
        assert self._reader is not None
        line = await self._reader.readline()
        if not line:
            raise EOFError("c-daemon closed the connection")
        text = line.decode("utf-8", errors="replace").strip()
        if not text:
            return ""
        try:
            msg = json.loads(text)
        except json.JSONDecodeError:
            # Daemon should always speak JSON; pass raw through just in case.
            return text
        if msg.get("type") == "exit":
            raise EOFError("c-daemon session exited")
        if msg.get("type") == "data":
            return str(msg.get("data", ""))
        return ""

    async def write(self, data: str) -> None:
        assert self._writer is not None
        payload = json.dumps({"type": "data", "data": data})
        self._writer.write((payload + "\n").encode("utf-8"))
        await self._writer.drain()

    async def resize(self, cols: int, rows: int) -> None:
        assert self._writer is not None
        payload = json.dumps({"type": "resize", "cols": cols, "rows": rows})
        self._writer.write((payload + "\n").encode("utf-8"))
        await self._writer.drain()

    async def close(self) -> None:
        if self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:  # pragma: no cover - best effort
                pass
            self._writer = None
            self._reader = None


async def try_open() -> CNativeBackend | None:
    """Open a C daemon session, or return None when unavailable.

    Availability probe doubles as the connect — no wasted round-trip.
    """
    if not is_daemon_available():
        return None
    backend = CNativeBackend()
    try:
        await backend.open()
        return backend
    except Exception as exc:
        log.debug("C daemon not reachable (%s); falling back", exc)
        return None
