from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.deal import Deal
from app.models.user import User
from app.schemas.crm import DealCreate, DealResponse, DealUpdate
from app.security import get_current_user

router = APIRouter(prefix="/crm/deals", tags=["crm"])

STAGES = ["lead", "qualified", "proposal", "negotiation", "won", "lost"]


@router.get("", response_model=list[DealResponse])
async def list_deals(
    stage: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Deal).where(Deal.user_id == user.id)
    if stage:
        q = q.where(Deal.stage == stage)
    result = await db.execute(q.order_by(Deal.updated_at.desc()))
    return result.scalars().all()


@router.post("", response_model=DealResponse, status_code=201)
async def create_deal(body: DealCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    deal = Deal(user_id=user.id, **body.model_dump())
    db.add(deal)
    await db.commit()
    await db.refresh(deal)
    return deal


@router.get("/{deal_id}", response_model=DealResponse)
async def get_deal(deal_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Deal).where(Deal.id == deal_id, Deal.user_id == user.id))
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@router.put("/{deal_id}", response_model=DealResponse)
async def update_deal(deal_id: int, body: DealUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Deal).where(Deal.id == deal_id, Deal.user_id == user.id))
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(deal, key, value)
    await db.commit()
    await db.refresh(deal)
    return deal


@router.put("/{deal_id}/stage", response_model=DealResponse)
async def move_stage(deal_id: int, stage: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if stage not in STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of: {STAGES}")
    result = await db.execute(select(Deal).where(Deal.id == deal_id, Deal.user_id == user.id))
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    deal.stage = stage
    await db.commit()
    await db.refresh(deal)
    return deal


@router.delete("/{deal_id}", status_code=204)
async def delete_deal(deal_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Deal).where(Deal.id == deal_id, Deal.user_id == user.id))
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    await db.delete(deal)
    await db.commit()
