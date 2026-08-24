# NOTICE: This file is protected under RCF-PL v2.0.3
"""Terminal backends package — one interface over every terminal transport.

Backends:
  - CNativeBackend  — aladdin-term C daemon (unix socket) — FIRST-CLASS
  - PtyBackend      — Python PTY fallback for local shells
  - SshBackend      — asyncssh channel to a user VM

The WS router resolves the right backend via :func:`open_local_backend`
(C first, PTY fallback) or constructs :class:`SshBackend` directly.
"""
from app.services.terminal_backends.base import (
    TerminalBackend,
    decode_message,
    encode_output,
)
from app.services.terminal_backends.c_native import CNativeBackend, try_open as _try_open_c
from app.services.terminal_backends.pty_backend import PtyBackend
from app.services.terminal_backends.ssh import SshBackend, connect_vm

__all__ = [
    "TerminalBackend",
    "CNativeBackend",
    "PtyBackend",
    "SshBackend",
    "connect_vm",
    "encode_output",
    "decode_message",
    "open_local_backend",
]


async def open_local_backend() -> tuple[TerminalBackend, str]:
    """Open a local terminal session: C daemon first, PTY fallback.

    Returns ``(backend, name)`` so callers can log which transport won.
    Never raises for "C not available" — that is an expected downgrade;
    only PTY failures propagate to the caller.
    """
    c_backend = await _try_open_c()
    if c_backend is not None:
        return c_backend, CNativeBackend.name

    pty_backend = PtyBackend()
    await pty_backend.open()
    return pty_backend, PtyBackend.name
