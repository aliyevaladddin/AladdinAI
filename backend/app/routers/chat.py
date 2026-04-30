import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent import Agent
from app.models.llm_provider import LLMProvider
from app.models.user import User
from app.schemas.router import ChatRequest, ChatResponse
from app.security import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not body.agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required (router auto-select coming soon)")

    result = await db.execute(select(Agent).where(Agent.id == body.agent_id, Agent.user_id == user.id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if not agent.llm_provider_id:
        raise HTTPException(status_code=400, detail="Agent has no LLM provider configured")

    result = await db.execute(select(LLMProvider).where(LLMProvider.id == agent.llm_provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="LLM provider not found")

    headers = {"Content-Type": "application/json"}
    if provider.api_key_encrypted:
        headers["Authorization"] = f"Bearer {provider.api_key_encrypted}"

    payload = {
        "model": agent.model,
        "messages": [
            {"role": "system", "content": agent.system_prompt},
            {"role": "user", "content": body.message},
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{provider.base_url}/v1/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            reply = data["choices"][0]["message"]["content"]
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {e}")

    return ChatResponse(response=reply, agent_name=agent.name, model=agent.model)
