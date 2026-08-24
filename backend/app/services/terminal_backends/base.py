# NOTICE: This file is protected under RCF-PL
"""TerminalBackend — one interface over every terminal transport.

All backends speak the same primitive protocol:

    read()  -> str    # decoded terminal output chunk (raises EOFError at end)
    write(data: str)  # keystrokes from the client
    resize(cols, rows)
    close()

Implementations adapt their underlying transport (C daemon unix socket,
Python PTY, asyncssh channel) to this shape, so the WebSocket router has
a single relay loop regardless of what is behind the terminal.

The C native backend is *first-class*: it is preferred whenever the
aladdin-term daemon socket is reachable; the Python PTY backend exists
as a fallback for environments without the binary.
"""
import json
import logging

log = logging.getLogger(__name__)


class TerminalBackend:
    """Abstract base for every terminal transport."""

    name: str = "base"

    async def open(self) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    async def read(self) -> str:  # pragma: no cover - interface
        """Return a decoded output chunk. Raise EOFError when the stream ends."""
        raise NotImplementedError

    async def write(self, data: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    async def resize(self, cols: int, rows: int) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    async def close(self) -> None:  # pragma: no cover - interface
        raise NotImplementedError


# Wire protocol shared between the browser and the WS router.
def encode_output(data: str) -> str:
    """Wrap raw terminal output into the wire message."""
    return json.dumps({"type": "data", "data": data})


def decode_message(raw: str) -> tuple[str, str] | None:
    """Parse a wire message into (type, payload). None if malformed."""
    try:
        msg = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(msg, dict):
        return None
    mtype = msg.get("type")
    if mtype == "data":
        return "data", str(msg.get("data", ""))
    if mtype == "resize":
        return "resize", msg
    return None
