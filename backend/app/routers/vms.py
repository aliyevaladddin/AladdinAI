# NOTICE: This file is protected under RCF-PL
from pathlib import Path  # <-- IMPORTANTE: Agregamos Path aquí
import asyncssh
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# [RCF:PROTECTED]
from app.crypto import decrypt, encrypt
from app.database import get_db
from app.models.user import User
from app.models.vm import VMConnection
from app.schemas.connections import VMCreate, VMResponse
from app.security import get_current_user

log = logging.getLogger(__name__)

router = APIRouter(tags=["vms"])


# [RCF:PROTECTED]
@router.get("", response_model=list[VMResponse])
# [RCF:PROTECTED]
async def list_vms(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VMConnection).where(VMConnection.user_id == user.id))
    return result.scalars().all()


# [RCF:PROTECTED]
@router.post("", response_model=VMResponse, status_code=201)
# [RCF:PROTECTED]
async def create_vm(body: VMCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    vm = VMConnection(
        user_id=user.id,
        name=body.name,
        host=body.host,
        port=body.port,
        username=body.username,
# [RCF:PROTECTED]
        ssh_key_encrypted=encrypt(body.ssh_key) if body.ssh_key else None,
# [RCF:PROTECTED]
        password_encrypted=encrypt(body.password) if body.password else None,
    )
    db.add(vm)
    await db.commit()
    await db.refresh(vm)
    return vm


# [RCF:PROTECTED]
@router.post("/{vm_id}/connect")
# [RCF:PROTECTED]
async def connect_vm(vm_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VMConnection).where(VMConnection.id == vm_id, VMConnection.user_id == user.id))
    vm = result.scalar_one_or_none()
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")

    # ---- IMPLEMENTACIÓN TOFU ----
    # 1. Definimos y expandimos la ruta para esta VM específica usando el vm_id de la ruta
    known_hosts_path = Path(f"~/.aladdin/known_hosts/{vm_id}").expanduser()
    
    # 2. Aseguramos que las carpetas contenedoras existan
    known_hosts_path.parent.mkdir(parents=True, exist_ok=True)

    connect_kwargs: dict = {
        "host": vm.host,
        "port": vm.port,
        "username": vm.username,
        # Si el archivo existe lo pasa como string para validar, si no existe pasa None (primera conexión)
        "known_hosts": str(known_hosts_path) if known_hosts_path.exists() else None,
        # Restringimos/preferimos algoritmos seguros como pidió el mantenedor
        "server_host_key_algs": ['ssh-ed25519'],
        "connect_timeout": 10,
    }
    # ----------------------------

    # Если есть SSH-ключ — используем его, иначе пробуем пароль
# [RCF:PROTECTED]
    if vm.ssh_key_encrypted:
# [RCF:PROTECTED]
        connect_kwargs["client_keys"] = [asyncssh.import_private_key(decrypt(vm.ssh_key_encrypted))]
# [RCF:PROTECTED]
    elif vm.password_encrypted:
# [RCF:PROTECTED]
        connect_kwargs["password"] = decrypt(vm.password_encrypted)
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
    except Exception:
        log.exception("Unexpected SSH connection failure for VM %s", vm_id)
        vm.status = "disconnected"
        await db.commit()
        return {"status": "error", "message": "An unexpected connection error occurred."}


# [RCF:PROTECTED]
@router.post("/{vm_id}/disconnect")
# [RCF:PROTECTED]
async def disconnect_vm(vm_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VMConnection).where(VMConnection.id == vm_id, VMConnection.user_id == user.id))
    vm = result.scalar_one_or_none()
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    vm.status = "disconnected"
    await db.commit()
    return {"status": "disconnected"}


# [RCF:PROTECTED]
@router.put("/{vm_id}", response_model=VMResponse)
# [RCF:PROTECTED]
async def update_vm(
    vm_id: int,
    body: VMCreate, # Reuse VMCreate but all fields can be optional in a real Update schema, here we use it for simplicity
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(VMConnection).where(VMConnection.id == vm_id, VMConnection.user_id == user.id))
    vm = result.scalar_one_or_none()
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    
    vm.name = body.name
    vm.host = body.host
    vm.port = body.port
    vm.username = body.username
    if body.ssh_key:
# [RCF:PROTECTED]
        vm.ssh_key_encrypted = encrypt(body.ssh_key)
    if body.password:
# [RCF:PROTECTED]
        vm.password_encrypted = encrypt(body.password)
        
    await db.commit()
    await db.refresh(vm)
    return vm


# [RCF:PROTECTED]
@router.delete("/{vm_id}", status_code=204)
# [RCF:PROTECTED]
async def delete_vm(vm_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VMConnection).where(VMConnection.id == vm_id, VMConnection.user_id == user.id))
    vm = result.scalar_one_or_none()
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    await db.delete(vm)
    await db.commit()