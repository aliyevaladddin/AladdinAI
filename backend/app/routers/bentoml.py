import asyncssh
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.bentoml_connection import BentoMLConnection
from app.models.user import User
from app.models.vm import VMConnection
from app.schemas.connections import BentoMLCreate, BentoMLResponse
from app.security import get_current_user

router = APIRouter(prefix="/bentoml", tags=["bentoml"])


class DeployRequest(BaseModel):
    vm_id: int
    service_name: str = "my_service:svc"
    port: int = 3000


@router.get("", response_model=list[BentoMLResponse])
async def list_bentoml(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BentoMLConnection).where(BentoMLConnection.user_id == user.id))
    return result.scalars().all()


@router.post("", response_model=BentoMLResponse, status_code=201)
async def create_bentoml(body: BentoMLCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    conn = BentoMLConnection(
        user_id=user.id,
        name=body.name,
        endpoint_url=body.endpoint_url,
        api_key_encrypted=body.api_key,
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)
    return conn


@router.post("/{conn_id}/test")
async def test_bentoml(conn_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BentoMLConnection).where(BentoMLConnection.id == conn_id, BentoMLConnection.user_id == user.id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    try:
        headers = {}
        if conn.api_key_encrypted:
            headers["Authorization"] = f"Bearer {conn.api_key_encrypted}"
        print(f"DEBUG: Testing BentoML health at {conn.endpoint_url}/healthz")
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{conn.endpoint_url}/healthz", headers=headers)
            resp.raise_for_status()
        conn.status = "connected"
        await db.commit()
        return {"status": "connected"}
    except Exception as e:
        print(f"DEBUG: BentoML test failed: {str(e)}")
        conn.status = "error"
        await db.commit()
        return {"status": "error", "message": str(e)}


@router.post("/{conn_id}/deploy")
async def deploy_bentoml(
    conn_id: int,
    body: DeployRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deploy BentoML service to a remote VM via SSH."""
    print(f"DEBUG: Starting deploy for BentoML {conn_id} to VM {body.vm_id}")
    # Find BentoML connection
    result = await db.execute(
        select(BentoMLConnection).where(
            BentoMLConnection.id == conn_id,
            BentoMLConnection.user_id == user.id,
        )
    )
    bentoml_conn = result.scalar_one_or_none()
    if not bentoml_conn:
        print("DEBUG: BentoML connection not found")
        raise HTTPException(status_code=404, detail="BentoML connection not found")

    # Find VM
    vm_result = await db.execute(
        select(VMConnection).where(
            VMConnection.id == body.vm_id,
            VMConnection.user_id == user.id,
        )
    )
    vm = vm_result.scalar_one_or_none()
    if not vm:
        print("DEBUG: VM not found")
        raise HTTPException(status_code=404, detail="VM not found")

    # Build SSH connection
    print(f"DEBUG: Connecting to SSH {vm.username}@{vm.host}:{vm.port}")
    connect_kwargs: dict = {
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

    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(3)
            if s.connect_ex((vm.host, vm.port)) != 0:
                print(f"DEBUG: Host {vm.host}:{vm.port} is not reachable via socket")
    except: pass

    try:
        async with asyncssh.connect(**connect_kwargs) as conn:
            print("DEBUG: SSH Connected. Checking for BentoML...")
            # Check if bentoml is installed
            check = await conn.run("bentoml --version", timeout=10)
            if check.exit_status != 0:
                print("DEBUG: BentoML not found, preparing environment and installing...")
                # Prepare environment for compilation on Termux
                await conn.run("pkg install -y clang python-dev make libffi-dev openssl-dev || true", timeout=60)
                
                # Install bentoml (heavy operation, needs 600s timeout)
                install = await conn.run(
                    "pip install bentoml --break-system-packages || pip3 install bentoml --break-system-packages", 
                    timeout=600
                )
                if install.exit_status != 0:
                    error_detail = install.stderr or install.stdout or "Unknown pip error"
                    print(f"DEBUG: Install failed: {error_detail[:500]}...")
                    return {
                        "status": "error",
                        "message": f"Failed to install BentoML. Error log: {error_detail[:200]}...",
                    }
                print("DEBUG: BentoML installed successfully")

            # Ensure lsof is present for port cleanup
            await conn.run("pkg install -y lsof || apt-get install -y lsof", timeout=30)

            # Kill any existing bentoml on this port
            print(f"DEBUG: Cleaning up port {body.port}")
            await conn.run(f"kill $(lsof -t -i :{body.port}) 2>/dev/null || true", timeout=5)

            # Start BentoML in background
            print(f"DEBUG: Starting BentoML serve {body.service_name}")
            start_cmd = (
                f"nohup bentoml serve {body.service_name} "
                f"--host 0.0.0.0 --port {body.port} "
                f"> /tmp/bentoml_{body.port}.log 2>&1 &"
            )
            start_result = await conn.run(start_cmd, timeout=10)

            # Update endpoint URL
            bentoml_conn.endpoint_url = f"http://{vm.host}:{body.port}"
            bentoml_conn.status = "deployed"
            await db.commit()
            print(f"DEBUG: Deploy successful to {bentoml_conn.endpoint_url}")

            return {
                "status": "deployed",
                "message": f"BentoML started on {vm.host}:{body.port}",
                "endpoint_url": bentoml_conn.endpoint_url,
                "log": "Service started in background. Check /tmp/bentoml_*.log for details.",
            }
    except Exception as e:
        print(f"DEBUG: SSH/Deploy failed: {str(e)}")
        return {"status": "error", "message": f"Deploy failed: {str(e)}"}



@router.delete("/{conn_id}", status_code=204)
async def delete_bentoml(conn_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BentoMLConnection).where(BentoMLConnection.id == conn_id, BentoMLConnection.user_id == user.id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    await db.delete(conn)
    await db.commit()

