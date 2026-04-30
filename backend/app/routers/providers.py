import json

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


@router.post("/{provider_id}/connect")
async def connect_provider(provider_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id, LLMProvider.user_id == user.id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    headers: dict = {"Content-Type": "application/json"}
    if provider.api_key_encrypted:
        headers["Authorization"] = f"Bearer {provider.api_key_encrypted}"

    try:
        if provider.type == "huggingface":
            # For Hugging Face, we verify the token and return recommended models
            headers = {"Authorization": f"Bearer {provider.api_key_encrypted}"}
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get("https://huggingface.co/api/whoami-v2", headers=headers)
                resp.raise_for_status()
            
            # Recommended models (including your MiniCPM3!)
            model_ids = [
                "openbmb/MiniCPM3-4B", 
                "google/gemma-2-9b-it",
                "mistralai/Mistral-7B-v0.3",
                "meta-llama/Meta-Llama-3-8B-Instruct"
            ]
            provider.status = "connected"
            provider.models_available = json.dumps(model_ids)
            await db.commit()
            return {"status": "connected", "models": model_ids, "count": len(model_ids)}

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{provider.base_url}/v1/models", headers=headers)
            resp.raise_for_status()

        data = resp.json()
        # Поддержка формата OpenAI-совместимых API (NVIDIA NIM, OpenAI, Ollama, и др.)
        models = data.get("data", data) if isinstance(data, dict) else data
        model_ids = [m.get("id", m) if isinstance(m, dict) else str(m) for m in models]

        provider.status = "connected"
        provider.models_available = json.dumps(model_ids)
        await db.commit()

        return {
            "status": "connected",
            "models": model_ids,
            "count": len(model_ids),
        }
    except httpx.HTTPStatusError as e:
        provider.status = "disconnected"
        await db.commit()
        return {"status": "error", "message": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except httpx.ConnectError:
        provider.status = "disconnected"
        await db.commit()
        return {"status": "error", "message": f"Cannot connect to {provider.base_url}. Check the URL."}
    except httpx.TimeoutException:
        provider.status = "disconnected"
        await db.commit()
        return {"status": "error", "message": "Connection timed out after 15 seconds."}
    except Exception as e:
        provider.status = "disconnected"
        await db.commit()
        return {"status": "error", "message": str(e)}


@router.get("/{provider_id}/models")
async def get_provider_models(provider_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id, LLMProvider.user_id == user.id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    if not provider.models_available:
        return {"models": [], "hint": "Connect the provider first to fetch available models."}

    models = json.loads(provider.models_available)
    return {"models": models, "count": len(models)}


@router.post("/{provider_id}/disconnect")
async def disconnect_provider(provider_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id, LLMProvider.user_id == user.id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    provider.status = "disconnected"
    await db.commit()
    return {"status": "disconnected"}


@router.delete("/{provider_id}", status_code=204)
async def delete_provider(provider_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id, LLMProvider.user_id == user.id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    await db.delete(provider)
    await db.commit()
