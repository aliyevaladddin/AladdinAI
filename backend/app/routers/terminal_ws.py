# NOTICE: This file is protected under RCF-PL
"""Terminal WebSocket endpoints.

All transports are reached through :mod:`app.services.terminal_backends`;
this router only handles auth, backend selection, and a single relay loop:

    browser ⇄ (JSON wire) ⇄ TerminalBackend ⇄ transport

Local terminals prefer the native C daemon (first-class) and fall back to
a Python PTY; VM terminals use asyncssh with TOFU known-hosts pinning.
"""
import asyncio
import logging
import json

import asyncssh
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.crypto import decrypt
from app.database import async_session
from app.models.vm import VMConnection
from app.security import get_current_user_ws
from app.services.terminal_backends import (
    SshBackend,
    connect_vm,
    decode_message,
    encode_output,
    open_local_backend,
)

log = logging.getLogger(__name__)

router = APIRouter(tags=["Terminal"])


# ── Shared relay ─────────────────────────────────────────────────────────────


async def _relay(websocket: WebSocket, backend) -> None:
    """Bidirectional pump between the browser socket and a TerminalBackend."""
    output_closed = asyncio.Event()

    async def pump_output():
        try:
            while True:
                data = await backend.read()
                if data:
                    await websocket.send_text(encode_output(data))
        except EOFError:
            log.debug("Terminal relay: %s backend EOF", backend.name)
        except Exception as ex:  # pragma: no cover - transport specific
            log.debug("Terminal relay: %s read loop ended: %s", backend.name, ex)
        finally:
            output_closed.set()

    reader_task = asyncio.create_task(pump_output())
    try:
        while True:
            raw = await websocket.receive_text()
            decoded = decode_message(raw)
            if decoded is None:
                continue
            mtype, payload = decoded
            if mtype == "data":
                await backend.write(payload)
            else:
                await backend.resize(
                    int(payload.get("cols", 80)),
                    int(payload.get("rows", 24)),
                )
    except WebSocketDisconnect:
        log.debug("Terminal relay: client disconnected")
    finally:
        if not output_closed.is_set():
            reader_task.cancel()
        try:
            await backend.close()
        except Exception:  # pragma: no cover - best effort
            pass
        try:
            await websocket.close()
        except Exception:  # pragma: no cover - already closed
            pass


async def _authenticate(websocket: WebSocket):
    """Validate the ?token= query param; returns the user or None (and closes)."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.send_text(json.dumps({"type": "error", "message": "Auth token missing"}))
        await websocket.close(code=1008)
        return None
    async with async_session() as db:
        try:
            return await get_current_user_ws(token, db)
        except Exception as e:
            log.warning("Terminal WS auth failed: %s", e)
            await websocket.send_text(json.dumps({"type": "error", "message": f"Auth failed: {str(e)}"}))
            await websocket.close(code=1008)
            return None


async def _send_error_and_close(websocket: WebSocket, message: str, code: int = 1011):
    await websocket.send_text(json.dumps({"type": "error", "message": message}))
    try:
        await websocket.close(code=code)
    except Exception:  # pragma: no cover
        pass


# ── Local terminal (C daemon first-class → PTY fallback) ─────────────────────


@router.websocket("/ws/terminal/local")
async def local_terminal_websocket(websocket: WebSocket):
    log.debug("Local terminal WS connection attempt")
    await websocket.accept()

    user = await _authenticate(websocket)
    if user is None:
        return

    backend, name = await open_local_backend()
    log.info("Local terminal WS for user %s using %s backend", user.id, name)
    await _relay(websocket, backend)


# ── VM terminal over SSH ──────────────────────────────────────────────────────


@router.websocket("/ws/terminal/{vm_id}")
async def terminal_websocket(websocket: WebSocket, vm_id: int):
    log.debug("Terminal WS attempt for VM %s", vm_id)
    await websocket.accept()

    user = await _authenticate(websocket)
    if user is None:
        return

    async with async_session() as db:
        result = await db.execute(
            select(VMConnection).where(
                VMConnection.id == vm_id,
                VMConnection.user_id == user.id,
            )
        )
        vm = result.scalar_one_or_none()
        if not vm:
            log.warning("Terminal WS: VM %s not found or access denied", vm_id)
            await _send_error_and_close(websocket, "VM not found", code=1003)
            return

        log.info("Terminal WS: connecting to %s:%s", vm.host, vm.port)

        password = decrypt(vm.password_encrypted) if vm.password_encrypted else None
        private_key = decrypt(vm.ssh_key_encrypted) if vm.ssh_key_encrypted else None

    conn = None
    try:
        conn = await connect_vm(
            host=vm.host,
            port=vm.port,
            username=vm.username,
            password=password,
            private_key=private_key,
        )
        backend = SshBackend(conn)
        await backend.open()
        log.info("Terminal WS: shell started for VM %s", vm_id)
        await _relay(websocket, backend)
    except asyncio.TimeoutError:
        log.warning("Terminal WS: SSH connection timeout for VM %s", vm_id)
        await _send_error_and_close(
            websocket,
            "\r\n\x1b[31mError: Connection Timeout. Is the VM/Phone reachable?\x1b[0m\r\n",
        )
    except asyncssh.PermissionDenied:
        log.warning("Terminal WS: SSH permission denied for VM %s", vm_id)
        await _send_error_and_close(
            websocket,
            "\r\n\x1b[31mError: Permission Denied. Check username/password.\x1b[0m\r\n",
        )
    except Exception as e:  # pragma: no cover - defensive
        log.exception("Terminal WS: unhandled error for VM %s", vm_id)
        await _send_error_and_close(
            websocket, f"\r\n\x1b[31mError: {str(e)}\x1b[0m\r\n"
        )
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:  # pragma: no cover - best effort
                pass
