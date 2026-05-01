import asyncssh
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.vm import VMConnection
from app.security import get_current_user

router = APIRouter(prefix="/ssh", tags=["ssh"])


class SSHExecRequest(BaseModel):
    vm_id: int
    command: str


class SSHExecResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int


@router.post("/exec", response_model=SSHExecResponse)
async def ssh_exec(
    body: SSHExecRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute a command on a remote VM via SSH."""
    result = await db.execute(
        select(VMConnection).where(
            VMConnection.id == body.vm_id,
            VMConnection.user_id == user.id,
        )
    )
    vm = result.scalar_one_or_none()
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")

    connect_kwargs: dict = {
        "host": vm.host,
        "port": vm.port,
        "username": vm.username,
        "known_hosts": None,
        "connect_timeout": 10,
    }

    if vm.ssh_key_encrypted:
        connect_kwargs["client_keys"] = [asyncssh.import_private_key(vm.ssh_key_encrypted)]
    elif vm.password_encrypted:
        connect_kwargs["password"] = vm.password_encrypted
    else:
        connect_kwargs["password"] = ""

    try:
        async with asyncssh.connect(**connect_kwargs) as conn:
            cmd_result = await conn.run(body.command, timeout=30)
            return SSHExecResponse(
                stdout=cmd_result.stdout or "",
                stderr=cmd_result.stderr or "",
                exit_code=cmd_result.exit_status or 0,
            )
    except asyncssh.PermissionDenied:
        raise HTTPException(status_code=403, detail="SSH permission denied. Check credentials.")
    except asyncssh.ConnectionLost:
        raise HTTPException(status_code=502, detail="SSH connection lost. Host may be unreachable.")
    except asyncssh.TimeoutError:
        raise HTTPException(status_code=504, detail="Command timed out after 30 seconds.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SSH error: {str(e)}")


@router.get("/vms-list")
async def list_vms_for_terminal(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List available VMs for the terminal SSH connect command."""
    result = await db.execute(
        select(VMConnection).where(VMConnection.user_id == user.id)
    )
    vms = result.scalars().all()
    return [
        {
            "id": vm.id,
            "name": vm.name,
            "host": vm.host,
            "port": vm.port,
            "username": vm.username,
            "status": vm.status,
        }
        for vm in vms
    ]
