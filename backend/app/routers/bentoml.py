from fastapi import APIRouter, Depends, HTTPException
import asyncssh
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session
from app.models import BentoMLConnection, VMConnection
from app.schemas.connections import BentoMLDeployRequest, BentoMLCreate
from app.security import get_current_user

router = APIRouter()

async def get_db():
    async with async_session() as session:
        yield session

@router.get("")
async def get_bentoml_connections(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BentoMLConnection))
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
        connect_kwargs["password"] = vm.password_encrypted

    try:
        async with asyncssh.connect(**connect_kwargs) as conn:
            print(f"DEBUG: SSH Connected. Deploying {body.service_name} inside Ubuntu...")
            
            # Check if bentoml is available inside Ubuntu
            check = await conn.run("proot-distro login ubuntu -- bentoml --version", timeout=60)
            
            if check.exit_status != 0:
                print(f"DEBUG: BentoML not found in Ubuntu. Error: {check.stderr}")
                return {"status": "error", "message": "BentoML not installed inside Ubuntu environment."}

            print("DEBUG: BentoML verified. Killing existing processes on port...")
            await conn.run(f"proot-distro login ubuntu -- bash -c 'fuser -k {body.port}/tcp || true'", timeout=30)

            print(f"DEBUG: Starting BentoML serve on port {body.port}...")
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
        import traceback
        error_trace = traceback.format_exc()
        print(f"DEBUG: Deploy error: {repr(e)}")
        print(f"DEBUG: Traceback: {error_trace}")
        return {"status": "error", "message": str(e) or repr(e), "traceback": error_trace}
