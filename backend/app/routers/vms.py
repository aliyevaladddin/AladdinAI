from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.vm import VMConnection
from app.schemas.connections import VMCreate, VMResponse
from app.security import get_current_user

router = APIRouter(prefix="/vms", tags=["vms"])


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
    )
    db.add(vm)
    await db.commit()
    await db.refresh(vm)
    return vm


@router.post("/{vm_id}/test")
async def test_vm(vm_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VMConnection).where(VMConnection.id == vm_id, VMConnection.user_id == user.id))
    vm = result.scalar_one_or_none()
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    # TODO: actual SSH connection test via asyncssh
    return {"status": "ok", "message": f"Connection test to {vm.host}:{vm.port} — placeholder"}


@router.delete("/{vm_id}", status_code=204)
async def delete_vm(vm_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VMConnection).where(VMConnection.id == vm_id, VMConnection.user_id == user.id))
    vm = result.scalar_one_or_none()
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    await db.delete(vm)
    await db.commit()
