import logging

from fastapi import APIRouter, Depends, HTTPException
import asyncssh
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.crypto import decrypt
from app.database import async_session
from app.models import BentoMLConnection, VMConnection
from app.schemas.connections import BentoMLDeployRequest, BentoMLCreate
from app.security import get_current_user

log = logging.getLogger(__name__)

router = APIRouter()

async def get_db():
    async with async_session() as session:
        yield session

@router.get("")
async def get_bentoml_connections(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    result = await db.execute(
        select(BentoMLConnection).where(BentoMLConnection.user_id == current_user.id)
    )
    return result.scalars().all()

@router.post("")
async def create_bentoml_connection(
    body: BentoMLCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    new_conn = BentoMLConnection(
        name=body.name,
        endpoint_url=body.endpoint_url,
        user_id=current_user.id,
        status="disconnected"
    )
    db.add(new_conn)
    await db.commit()
    await db.refresh(new_conn)
    return new_conn

@router.post("/{conn_id}/deploy")
async def deploy_service(
    conn_id: int, 
    body: BentoMLDeployRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    result = await db.execute(
        select(BentoMLConnection).where(
            BentoMLConnection.id == conn_id,
            BentoMLConnection.user_id == current_user.id
        )
    )
    bentoml_conn = result.scalar_one_or_none()
    
    if not bentoml_conn:
        raise HTTPException(status_code=404, detail="BentoML Connection not found")

    # Get the first VM of this user
    vm_result = await db.execute(
        select(VMConnection).where(VMConnection.user_id == current_user.id)
    )
    vm = vm_result.scalar_one_or_none()
    
    if not vm:
        raise HTTPException(status_code=404, detail="No VM found for this user to deploy on")

    connect_kwargs = {
        "host": vm.host,
        "port": vm.port,
        "username": vm.username,
        "known_hosts": None
    }
    # Note: Use vm.password_encrypted if needed as per main.py
    if hasattr(vm, 'password_encrypted') and vm.password_encrypted:
        connect_kwargs["password"] = decrypt(vm.password_encrypted)

    try:
        async with asyncssh.connect(**connect_kwargs) as conn:
            log.info("bentoml: SSH connected, deploying %s inside Ubuntu", body.service_name)

            # Check if bentoml is available inside Ubuntu
            check = await conn.run("proot-distro login ubuntu -- bentoml --version", timeout=60)

            if check.exit_status != 0:
                log.warning("bentoml: not found in Ubuntu env: %s", check.stderr)
                return {"status": "error", "message": "BentoML not installed inside Ubuntu environment."}

            log.debug("bentoml: verified, killing existing processes on port %s", body.port)
            await conn.run(f"proot-distro login ubuntu -- bash -c 'fuser -k {body.port}/tcp || true'", timeout=30)

            log.info("bentoml: starting serve %s on port %s", body.service_name, body.port)
            start_cmd = (
                f"proot-distro login ubuntu -- bash -c 'nohup bentoml serve {body.service_name} "
                f"--host 0.0.0.0 --port {body.port} > ~/bentoml_{body.port}.log 2>&1 &'"
            )
            await conn.run(start_cmd, timeout=30)

            # Update DB
            bentoml_conn.endpoint_url = f"http://{vm.host}:{body.port}"
            bentoml_conn.status = "deployed"
            await db.commit()

            return {"status": "success", "message": f"Successfully deployed to {bentoml_conn.endpoint_url}"}

    except Exception as e:
        log.exception("bentoml: deploy failed")
        return {"status": "error", "message": "An unexpected error occurred during deployment."}


@router.put("/{conn_id}")
async def update_bentoml_connection(
    conn_id: int,
    body: BentoMLCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    result = await db.execute(
        select(BentoMLConnection).where(
            BentoMLConnection.id == conn_id,
            BentoMLConnection.user_id == current_user.id
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="BentoML Connection not found")
    
    conn.name = body.name
    conn.endpoint_url = body.endpoint_url
    # API Key is not in the model but the frontend sends it, we can ignore or add to config if needed
    
    await db.commit()
    await db.refresh(conn)
    return conn


@router.post("/{conn_id}/test")
async def test_bentoml(conn_id: int, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    result = await db.execute(
        select(BentoMLConnection).where(BentoMLConnection.id == conn_id, BentoMLConnection.user_id == user.id)
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    # Simple health check simulation or real check if endpoint is public
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(f"{conn.endpoint_url}/healthz")
            if res.status_code == 200:
                conn.status = "connected"
                await db.commit()
                return {"status": "connected", "message": "Health check passed"}
            else:
                conn.status = "error"
                await db.commit()
                return {"status": "error", "message": f"Health check returned {res.status_code}"}
    except Exception as e:
        log.exception("bentoml: health check connection failed")
        conn.status = "disconnected"
        await db.commit()
        return {"status": "error", "message": "An unexpected error occurred during the health check."}


@router.delete("/{conn_id}", status_code=204)
async def delete_bentoml_connection(
    conn_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    result = await db.execute(
        select(BentoMLConnection).where(
            BentoMLConnection.id == conn_id,
            BentoMLConnection.user_id == current_user.id
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="BentoML Connection not found")
    
    await db.delete(conn)
    await db.commit()
