import asyncssh
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.vm import VMConnection
from app.schemas.connections import VMCreate, VMResponse
from app.security import get_current_user

router = APIRouter(tags=["vms"])


@router.get("", response_model=list[VMResponse])
async def list_vms(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VMConnection).where(VMConnection.user_id == user.id))
    return result.scalars().all()


@router.post("", response_model=VMResponse, status_code=201)
async def create_vm(body: VMCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    vm = VMConnection(
        user_id=user.id,
        name=body.name,
        host=body.host,
        port=body.port,
        username=body.username,
        ssh_key_encrypted=body.ssh_key,
        password_encrypted=body.password,
    )
    db.add(vm)
    await db.commit()
    await db.refresh(vm)
    return vm


@router.post("/{vm_id}/connect")
async def connect_vm(vm_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VMConnection).where(VMConnection.id == vm_id, VMConnection.user_id == user.id))
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

    # Если есть SSH-ключ — используем его, иначе пробуем пароль
    if vm.ssh_key_encrypted:
        connect_kwargs["client_keys"] = [asyncssh.import_private_key(vm.ssh_key_encrypted)]
    elif vm.password_encrypted:
        connect_kwargs["password"] = vm.password_encrypted
    else:
        connect_kwargs["password"] = ""

    try:
        async with asyncssh.connect(**connect_kwargs) as conn:
            result_cmd = await conn.run("echo ok", check=True)
            output = result_cmd.stdout.strip()

        vm.status = "connected"
        await db.commit()
        return {"status": "connected", "message": f"SSH connection to {vm.host}:{vm.port} successful. Response: {output}"}
    except asyncssh.PermissionDenied:
        vm.status = "disconnected"
        await db.commit()
        return {"status": "error", "message": "Permission denied. Check credentials or SSH key."}
    except asyncssh.ConnectionLost:
        vm.status = "disconnected"
        await db.commit()
        return {"status": "error", "message": "Connection lost. Host may be unreachable."}
    except Exception as e:
        vm.status = "disconnected"
        await db.commit()
        return {"status": "error", "message": str(e)}


@router.post("/{vm_id}/disconnect")
async def disconnect_vm(vm_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VMConnection).where(VMConnection.id == vm_id, VMConnection.user_id == user.id))
    vm = result.scalar_one_or_none()
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    vm.status = "disconnected"
    await db.commit()
    return {"status": "disconnected"}


@router.delete("/{vm_id}", status_code=204)
async def delete_vm(vm_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VMConnection).where(VMConnection.id == vm_id, VMConnection.user_id == user.id))
    vm = result.scalar_one_or_none()
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    await db.delete(vm)
    await db.commit()
