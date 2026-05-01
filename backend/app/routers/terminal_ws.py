import asyncio
import asyncssh
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from app.database import async_session
from app.models.vm import VMConnection
from app.security import get_current_user_ws
import json

router = APIRouter(prefix="/ws/terminal", tags=["Terminal WS"])

@router.websocket("/{vm_id}")
async def terminal_websocket(
    websocket: WebSocket,
    vm_id: int
):
    print(f"DEBUG: WebSocket connection attempt for VM {vm_id}")
    await websocket.accept()
    
    # Verify authentication
    token = websocket.query_params.get("token")
    if not token:
        await websocket.send_text(json.dumps({"type": "error", "message": "Authentication token missing"}))
        await websocket.close(code=1008)
        return
    
    async with async_session() as db:
        try:
            user = await get_current_user_ws(token, db)
        except Exception as e:
            await websocket.send_text(json.dumps({"type": "error", "message": f"Auth failed: {str(e)}"}))
            await websocket.close(code=1008)
            return

        # Find VM
        result = await db.execute(
            select(VMConnection).where(
                VMConnection.id == vm_id,
                VMConnection.user_id == user.id
            )
        )
        vm = result.scalar_one_or_none()
        if not vm:
            await websocket.send_text(json.dumps({"type": "error", "message": "VM not found"}))
            await websocket.close(code=1003)
            return

        # SSH Connection parameters
        connect_kwargs = {
            "host": vm.host,
            "port": vm.port,
            "username": vm.username,
            "known_hosts": None,
            "connect_timeout": 15,
        }
        if vm.ssh_key_encrypted:
            connect_kwargs["client_keys"] = [asyncssh.import_private_key(vm.ssh_key_encrypted)]
        elif vm.password_encrypted:
            connect_kwargs["password"] = vm.password_encrypted

        try:
            async with asyncssh.connect(**connect_kwargs) as conn:
                async with conn.create_session(asyncssh.SSHClientSession, term_type='xterm-256color', term_size=(80, 24)) as (stdin, stdout, stderr):
                    
                    async def pipe_stdout():
                        try:
                            while True:
                                data = await stdout.read(4096)
                                if not data:
                                    break
                                await websocket.send_text(json.dumps({"type": "data", "data": data}))
                        except Exception as e:
                            print(f"Stdout pipe error: {e}")

                    async def pipe_stderr():
                        try:
                            while True:
                                data = await stderr.read(4096)
                                if not data:
                                    break
                                await websocket.send_text(json.dumps({"type": "data", "data": data}))
                        except Exception as e:
                            print(f"Stderr pipe error: {e}")

                    stdout_task = asyncio.create_task(pipe_stdout())
                    stderr_task = asyncio.create_task(pipe_stderr())

                    try:
                        while True:
                            msg_text = await websocket.receive_text()
                            msg = json.loads(msg_text)
                            
                            if msg["type"] == "data":
                                stdin.write(msg["data"])
                            elif msg["type"] == "resize":
                                # We could support terminal resizing here
                                pass
                    except WebSocketDisconnect:
                        print("WebSocket disconnected")
                    except Exception as e:
                        print(f"WebSocket processing error: {e}")
                    finally:
                        stdout_task.cancel()
                        stderr_task.cancel()
                        
        except Exception as e:
            await websocket.send_text(json.dumps({"type": "error", "message": f"SSH connection failed: {str(e)}"}))
            await websocket.close()
