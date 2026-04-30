import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.llm_provider import LLMProvider
from app.models.user import User
from app.schemas.connections import LLMProviderCreate, LLMProviderResponse
from app.security import get_current_user

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=list[LLMProviderResponse])
async def list_providers(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMProvider).where(LLMProvider.user_id == user.id))
    return result.scalars().all()


@router.post("", response_model=LLMProviderResponse, status_code=201)
async def create_provider(body: LLMProviderCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    provider = LLMProvider(
        user_id=user.id,
        name=body.name,
        type=body.type,
        api_key_encrypted=body.api_key,
        base_url=body.base_url,
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return provider


@router.post("/{provider_id}/test")
async def test_provider(provider_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id, LLMProvider.user_id == user.id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    try:
        headers = {}
        if provider.api_key_encrypted:
            headers["Authorization"] = f"Bearer {provider.api_key_encrypted}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{provider.base_url}/v1/models", headers=headers)
            resp.raise_for_status()
        return {"status": "connected", "models": resp.json()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.delete("/{provider_id}", status_code=204)
async def delete_provider(provider_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id, LLMProvider.user_id == user.id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    await db.delete(provider)
    await db.commit()
