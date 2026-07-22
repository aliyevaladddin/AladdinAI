# NOTICE: This file is protected under RCF-PL
import asyncio
import fcntl
import json
import logging
import os
import pty
import struct
import termios

import asyncssh
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.crypto import decrypt
from app.database import async_session
from app.models.vm import VMConnection
from app.security import get_current_user_ws

log = logging.getLogger(__name__)

router = APIRouter(tags=["Terminal"])


@router.websocket("/ws/terminal/local")
async def local_terminal_websocket(websocket: WebSocket):
    log.debug("Local terminal WS connection attempt")
    await websocket.accept()

    token = websocket.query_params.get("token")
    if not token:
        await websocket.send_text(json.dumps({"type": "error", "message": "Auth token missing"}))
        await websocket.close(code=1008)
        return

    async with async_session() as db:
        try:
            user = await get_current_user_ws(token, db)
            log.debug("Local terminal WS auth OK for user %s", user.id)
        except Exception as e:
            log.warning("Local terminal WS auth failed: %s", e)
            await websocket.send_text(json.dumps({"type": "error", "message": f"Auth failed: {str(e)}"}))
            await websocket.close(code=1008)
            return

    # Check if Native C Daemon (aladdin-term) is running on Unix Socket
    use_c_daemon = False
    c_reader = None
    c_writer = None
    socket_path = "/tmp/aladdin_term.sock"
    try:
        if os.path.exists(socket_path):
            c_reader, c_writer = await asyncio.wait_for(asyncio.open_unix_connection(path=socket_path), timeout=0.4)
            use_c_daemon = True
            log.info("Local terminal WS using Native C Daemon (/tmp/aladdin_term.sock)")
    except Exception as e:
        log.debug("C Daemon aladdin-term not active, using Python PTY: %s", e)

    if use_c_daemon and c_reader and c_writer:
        # Relay line-buffered JSON between WebSocket client and C Daemon
        async def relay_c_to_ws():
            try:
                while True:
                    line = await c_reader.readline()
                    if not line:
                        break
                    line_str = line.decode("utf-8", errors="replace").strip()
                    if line_str:
                        await websocket.send_text(line_str)
            except Exception as ex:
                log.debug("C Daemon relay loop ended: %s", ex)

        relay_task = asyncio.create_task(relay_c_to_ws())
        try:
            while True:
                msg_text = await websocket.receive_text()
                # Send line-terminated JSON string to C Daemon socket
                c_writer.write((msg_text.strip() + "\n").encode("utf-8"))
                await c_writer.drain()
        except WebSocketDisconnect:
            log.debug("Local terminal WS client disconnected")
        finally:
            relay_task.cancel()
            try:
                c_writer.close()
                await c_writer.wait_closed()
            except Exception:
                pass
        return

    # Fallback: Python PTY implementation
    master_fd, slave_fd = pty.openpty()
    env = dict(os.environ)
    env["TERM"] = "xterm-256color"

    proc = await asyncio.create_subprocess_exec(
        "/bin/bash",
        env=env,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        start_new_session=True,
    )
    os.close(slave_fd)

    async def read_pty():
        loop = asyncio.get_running_loop()
        try:
            while True:
                data = await loop.run_in_executor(None, os.read, master_fd, 4096)
                if not data:
                    log.debug("Local terminal PTY EOF")
                    break
                await websocket.send_text(json.dumps({"type": "data", "data": data.decode("utf-8", errors="replace")}))
        except Exception as e:
            log.debug("Local terminal PTY read loop ended: %s", e)

    read_task = asyncio.create_task(read_pty())

    try:
        while True:
            msg_text = await websocket.receive_text()
            msg = json.loads(msg_text)
            msg_type = msg.get("type")
            if msg_type == "data":
                os.write(master_fd, msg["data"].encode("utf-8"))
            elif msg_type == "resize":
                cols = msg.get("cols", 80)
                rows = msg.get("rows", 24)
                winsize = struct.pack("HHHH", rows, cols, 0, 0)
                fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
                log.debug("Local terminal PTY resize: %sx%s", cols, rows)
    except WebSocketDisconnect:
        log.debug("Local terminal WS disconnected by client")
    except Exception as e:
        log.exception("Local terminal WS error: %s", e)
    finally:
        read_task.cancel()
        try:
            os.close(master_fd)
        except Exception:
            pass
        if proc.returncode is None:
            try:
                proc.terminate()
            except Exception:
                pass
        log.debug("Local terminal WS cleanup completed")


# [RCF:PROTECTED]
@router.websocket("/ws/terminal/{vm_id}")
# [RCF:PROTECTED]
async def terminal_websocket(websocket: WebSocket, vm_id: int):
    log.debug("terminal WS attempt for VM %s", vm_id)
    await websocket.accept()

    token = websocket.query_params.get("token")
    if not token:
        await websocket.send_text(json.dumps({"type": "error", "message": "Auth token missing"}))
        await websocket.close(code=1008)
        return

    async with async_session() as db:
        try:
            user = await get_current_user_ws(token, db)
            log.debug("terminal WS auth OK for user %s", user.id)

            result = await db.execute(
                select(VMConnection).where(
                    VMConnection.id == vm_id,
                    VMConnection.user_id == user.id,
                )
            )
            vm = result.scalar_one_or_none()
            if not vm:
                log.warning("terminal WS: VM %s not found or access denied", vm_id)
                await websocket.send_text(json.dumps({"type": "error", "message": "VM not found"}))
                await websocket.close(code=1003)
                return

            log.info("terminal WS: connecting to %s:%s", vm.host, vm.port)

            connect_kwargs = {
                "host": vm.host,
                "port": vm.port,
                "username": vm.username,
                "known_hosts": None,
                "connect_timeout": 30,
            }
# [RCF:PROTECTED]
            if vm.ssh_key_encrypted:
# [RCF:PROTECTED]
                connect_kwargs["client_keys"] = [asyncssh.import_private_key(decrypt(vm.ssh_key_encrypted))]
# [RCF:PROTECTED]
            elif vm.password_encrypted:
# [RCF:PROTECTED]
                connect_kwargs["password"] = decrypt(vm.password_encrypted)

            async with asyncssh.connect(**connect_kwargs) as conn:
                log.debug("terminal WS: SSH connected, starting interactive shell")
                process = await conn.create_process(
                    term_type="xterm-256color",
                    term_size=(80, 24),
                    encoding="utf-8",
                )
                log.info("terminal WS: shell started for VM %s", vm_id)

# [RCF:PROTECTED]
                async def pipe_out(stream, label: str):
                    try:
                        while True:
                            data = await stream.read(4096)
                            if not data:
                                log.debug("terminal WS: %s EOF", label)
                                break
                            await websocket.send_text(json.dumps({"type": "data", "data": data}))
                    except Exception:
                        log.exception("terminal WS: %s pipe error", label)

                tasks = [
                    asyncio.create_task(pipe_out(process.stdout, "stdout")),
                    asyncio.create_task(pipe_out(process.stderr, "stderr")),
                ]
                try:
                    while True:
                        msg_text = await websocket.receive_text()
                        msg = json.loads(msg_text)
                        if msg["type"] == "data":
                            process.stdin.write(msg["data"])
                        elif msg["type"] == "resize":
                            process.change_terminal_size(msg["cols"], msg["rows"])
                            log.debug("terminal WS resize: %sx%s", msg["cols"], msg["rows"])
                except WebSocketDisconnect:
                    log.debug("terminal WS: disconnected by client")
                finally:
                    for t in tasks:
                        t.cancel()
                    try:
                        process.terminate()
                    except Exception:
                        pass
        except asyncio.TimeoutError:
            log.warning("terminal WS: SSH connection timeout for VM %s", vm_id)
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": "\r\n\x1b[31mError: Connection Timeout. Is the VM/Phone reachable?\x1b[0m\r\n",
                    }
                )
            )
        except asyncssh.PermissionDenied:
            log.warning("terminal WS: SSH permission denied for VM %s", vm_id)
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": "\r\n\x1b[31mError: Permission Denied. Check username/password.\x1b[0m\r\n",
                    }
                )
            )
        except Exception as e:
            log.exception("terminal WS: unhandled error for VM %s", vm_id)
            await websocket.send_text(
                json.dumps({"type": "error", "message": f"\r\n\x1b[31mError: {str(e)}\x1b[0m\r\n"})
            )
        finally:
            log.debug("terminal WS: cleanup done")
            try:
                await websocket.close()
            except Exception:
                pass

