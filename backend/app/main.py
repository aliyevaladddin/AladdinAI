# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
import asyncio
import asyncssh
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.database import async_session
from app.models.vm import VMConnection
from app.security import get_current_user_ws
from app.routers import (
    agents, auth, bentoml, channels_email, channels_messaging,
    chat, crm_activities, crm_contacts, crm_deals, dashboard, mongodb,
    providers, router_config, ssh_exec, vms, webhooks
)

app = FastAPI(title="AladdinAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/terminal/{vm_id}")
async def terminal_websocket(websocket: WebSocket, vm_id: int):
    print(f"DEBUG: Root WebSocket attempt for VM {vm_id}")
    await websocket.accept()
    
    token = websocket.query_params.get("token")
    if not token:
        await websocket.send_text(json.dumps({"type": "error", "message": "Auth token missing"}))
        await websocket.close(code=1008)
        return

    async with async_session() as db:
        try:
            user = await get_current_user_ws(token, db)
            print(f"DEBUG: Auth successful for user {user.id}")
            
            result = await db.execute(
                select(VMConnection).where(
                    VMConnection.id == vm_id,
                    VMConnection.user_id == user.id
                )
            )
            vm = result.scalar_one_or_none()
            if not vm:
                print(f"DEBUG: VM {vm_id} not found or access denied")
                await websocket.send_text(json.dumps({"type": "error", "message": "VM not found"}))
                await websocket.close(code=1003)
                return

            print(f"DEBUG: VM found: {vm.host}:{vm.port}. Attempting SSH...")

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

            async with asyncssh.connect(**connect_kwargs) as conn:
                print("DEBUG: SSH connected! Opening session...")
                stdin, stdout, stderr = await conn.open_session(term_type='xterm-256color', term_size=(80, 24))
                print("DEBUG: SSH Session opened!")
                
                async def pipe_out(stream):
                    try:
                        while True:
                            data = await stream.read(4096)
                            if not data: break
                            await websocket.send_text(json.dumps({"type": "data", "data": data}))
                    except Exception as e:
                        print(f"DEBUG: Stream pipe error: {e}")

                tasks = [asyncio.create_task(pipe_out(stdout)), asyncio.create_task(pipe_out(stderr))]
                try:
                    while True:
                        msg_text = await websocket.receive_text()
                        msg = json.loads(msg_text)
                        if msg["type"] == "data": 
                            stdin.write(msg["data"])
                        elif msg["type"] == "resize":
                            stdin.channel.change_terminal_size(msg["cols"], msg["rows"])
                            print(f"DEBUG: Terminal resized to {msg['cols']}x{msg['rows']}")
                except WebSocketDisconnect:
                    print("DEBUG: WebSocket disconnected by client")
                finally: 
                    for t in tasks: t.cancel()
                    print("DEBUG: SSH cleanup done")
        except Exception as e:
            print(f"DEBUG: Terminal General Error: {e}")
            import traceback
            traceback.print_exc()
            try:
                if websocket.client_state.name != "DISCONNECTED":
                    await websocket.close()
            except: pass

app.include_router(auth.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(providers.router, prefix="/api")
app.include_router(router_config.router, prefix="/api")
app.include_router(channels_messaging.router, prefix="/api")
app.include_router(channels_email.router, prefix="/api")
app.include_router(crm_contacts.router, prefix="/api")
app.include_router(crm_deals.router, prefix="/api")
app.include_router(crm_activities.router, prefix="/api")
app.include_router(vms.router, prefix="/api/vms")
app.include_router(mongodb.router, prefix="/api")
app.include_router(bentoml.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")
app.include_router(ssh_exec.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "AladdinAI API is running", "version": "0.1.0", "protocol": "RCF/2.0.3"}
