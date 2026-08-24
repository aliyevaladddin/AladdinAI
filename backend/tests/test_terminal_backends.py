# NOTICE: This file is protected under RCF-PL
"""Tests for the unified TerminalBackend abstraction.

Covers wire helpers, CNativeBackend JSON framing (with mocked streams),
PtyBackend against a real PTY, and the local resolver priority
(C first-class → PTY fallback).
"""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.terminal_backends import (
    CNativeBackend,
    PtyBackend,
    decode_message,
    encode_output,
    open_local_backend,
)
from app.services.terminal_backends.base import TerminalBackend


# ── Wire protocol ────────────────────────────────────────────────────────────

def test_encode_output_wraps_data():
    assert json.loads(encode_output("hi")) == {"type": "data", "data": "hi"}


def test_decode_message_variants():
    assert decode_message('{"type":"data","data":"ls"}') == ("data", "ls")
    msg = decode_message('{"type":"resize","cols":120,"rows":40}')
    assert msg is not None
    mtype, payload = msg
    assert mtype == "resize"
    assert payload["cols"] == 120
    assert decode_message("not json") is None
    assert decode_message('{"type":"bogus"}') is None
    assert decode_message("[]") is None


# ── CNativeBackend framing ───────────────────────────────────────────────────

def _make_c_backend(reader, writer) -> CNativeBackend:
    b = CNativeBackend()
    b._reader = reader
    b._writer = writer
    return b


@pytest.mark.asyncio
async def test_c_native_read_extracts_data():
    reader = MagicMock()
    reader.readline = AsyncMock(return_value=b'{"type":"data","data":"hello"}\n')
    backend = _make_c_backend(reader, MagicMock())
    assert await backend.read() == "hello"


@pytest.mark.asyncio
async def test_c_native_exit_raises_eof():
    reader = MagicMock()
    reader.readline = AsyncMock(return_value=b'{"type":"exit"}\n')
    backend = _make_c_backend(reader, MagicMock())
    with pytest.raises(EOFError):
        await backend.read()


@pytest.mark.asyncio
async def test_c_native_eof_on_closed_socket():
    reader = MagicMock()
    reader.readline = AsyncMock(return_value=b"")
    backend = _make_c_backend(reader, MagicMock())
    with pytest.raises(EOFError):
        await backend.read()


@pytest.mark.asyncio
async def test_c_native_write_sends_json_line():
    writer = MagicMock()
    writer.drain = AsyncMock()
    backend = _make_c_backend(MagicMock(), writer)
    await backend.write("echo hi")
    sent = writer.write.call_args[0][0].decode()
    assert json.loads(sent) == {"type": "data", "data": "echo hi"}
    assert sent.endswith("\n")


@pytest.mark.asyncio
async def test_c_native_resize_sends_dims():
    writer = MagicMock()
    writer.drain = AsyncMock()
    backend = _make_c_backend(MagicMock(), writer)
    await backend.resize(100, 30)
    sent = json.loads(writer.write.call_args[0][0].decode())
    assert sent == {"type": "resize", "cols": 100, "rows": 30}


# ── Local resolver: C first-class, PTY fallback ─────────────────────────────

@pytest.mark.asyncio
async def test_resolver_prefers_c_daemon():
    fake_c = MagicMock(spec=TerminalBackend)
    fake_c.name = "c-native"
    with patch("app.services.terminal_backends._try_open_c", new=AsyncMock(return_value=fake_c)):
        backend, name = await open_local_backend()
        assert name == "c-native"
        assert backend is fake_c


@pytest.mark.asyncio
async def test_resolver_falls_back_to_pty():
    with patch("app.services.terminal_backends._try_open_c", new=AsyncMock(return_value=None)):
        with patch.object(PtyBackend, "open", new=AsyncMock()):
            backend, name = await open_local_backend()
            assert name == "pty"
            assert isinstance(backend, PtyBackend)


# ── PtyBackend (real PTY — cheap on linux) ──────────────────────────────────

@pytest.mark.asyncio
async def test_pty_backend_echo_and_resize():
    backend = PtyBackend()
    await backend.open()
    try:
        await backend.write("echo pty_test_marker\n")
        # Read output until marker or timeout
        got = ""
        for _ in range(50):
            try:
                got += await asyncio.wait_for(backend.read(), timeout=0.2)
            except asyncio.TimeoutError:
                continue
            if "pty_test_marker" in got:
                break
        assert "pty_test_marker" in got
        await backend.resize(100, 30)  # must not raise
    finally:
        await backend.close()
