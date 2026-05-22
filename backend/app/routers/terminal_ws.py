import asyncio
import json
import logging

import asyncssh
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.crypto import decrypt
from app.database import async_session
from app.models.vm import VMConnection
from app.security import get_current_user_ws

log = logging.getLogger(__name__)

router = APIRouter(tags=["Terminal WS"])


@router.websocket("/ws/terminal/{vm_id}")
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
            if vm.ssh_key_encrypted:
                connect_kwargs["client_keys"] = [asyncssh.import_private_key(decrypt(vm.ssh_key_encrypted))]
            elif vm.password_encrypted:
                connect_kwargs["password"] = decrypt(vm.password_encrypted)

            async with asyncssh.connect(**connect_kwargs) as conn:
                log.debug("terminal WS: SSH connected, starting interactive shell")
                # create_process() with term_type requests a PTY and, when no command
                # is given, runs the user's login shell — which is what makes a black
                # interactive pane actually produce a prompt. open_session() alone
                # was opening a channel but never starting any program, so stdout
                # stayed silent and the xterm pane looked frozen.
                process = await conn.create_process(
                    term_type="xterm-256color",
                    term_size=(80, 24),
                    encoding="utf-8",
                )
                log.info("terminal WS: shell started for VM %s", vm_id)

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
