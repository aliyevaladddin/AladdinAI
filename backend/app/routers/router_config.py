from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.router_config import RouterConfig
from app.models.user import User
from app.schemas.router import RouterConfigCreate, RouterConfigResponse, RouterConfigUpdate
from app.security import get_current_user

router = APIRouter(prefix="/router", tags=["router"])


@router.get("", response_model=list[RouterConfigResponse])
async def list_configs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RouterConfig).where(RouterConfig.user_id == user.id))
    return result.scalars().all()


@router.post("", response_model=RouterConfigResponse, status_code=201)
async def create_config(body: RouterConfigCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    config = RouterConfig(user_id=user.id, **body.model_dump())
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


@router.put("/{config_id}", response_model=RouterConfigResponse)
async def update_config(config_id: int, body: RouterConfigUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RouterConfig).where(RouterConfig.id == config_id, RouterConfig.user_id == user.id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(config, key, value)
    await db.commit()
    await db.refresh(config)
    return config


@router.delete("/{config_id}", status_code=204)
async def delete_config(config_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RouterConfig).where(RouterConfig.id == config_id, RouterConfig.user_id == user.id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    await db.delete(config)
    await db.commit()
