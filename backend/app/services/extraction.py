"""Per-message memory extraction.

After an agent finishes a turn, optionally distill the exchange into a small
set of facts and persist them via the same gates/safety pipeline that backs
the explicit `remember` tool.

Config lives in `agent.tools_config.extraction`:

    {
      "extraction": {
        "enabled": true,
        "model": "<nim model id>" | null,
        "max_facts": 5
      }
    }

Resolution order for the model: per-check `model` -> `default_safety_model`
-> `default_gate_model` -> agent's main model. If none resolve, extraction
is skipped entirely.

Failure mode: silent. Extraction is best-effort and must never affect the
user-facing reply. Errors are logged and swallowed.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.agent import Agent
from app.models.llm_provider import LLMProvider
from app.services import memory as mem_service
from app.services.gates import gate_memory_write
from app.services.llm_service import chat_completion
from app.services.memory import MemoryError as MemSvcError
from app.services.safety import safety_pii

log = logging.getLogger(__name__)

EXTRACTION_TIMEOUT = 20.0
EXTRACTION_MAX_TOKENS = 768
DEFAULT_MAX_FACTS = 5

_SYSTEM_PROMPT = (
    "You distill a short conversation snippet into durable facts worth saving "
    "in long-term memory. Extract only stable information: names, preferences, "
    "decisions, deadlines, IDs, contact details, agreed-upon plans. Skip "
    "greetings, acknowledgements, ephemeral reasoning, and anything already "
    "implied by the system prompt. "
    'Reply with strict JSON: {"facts": [{"text": "<one sentence>", '
    '"visibility": "private"|"shared", "tags": ["<tag>", ...]}]}. '
    "Visibility rules: use 'shared' for any fact about the user themselves "
    "(their name, email, phone, address, role, company, languages, personal "
    "preferences, recurring deadlines) AND for customer/contact-level facts "
    "useful to other agents serving the same user. Use 'private' only for "
    "agent-internal notes that have no value to siblings (e.g. this agent's "
    "draft state, intermediate reasoning, agent-specific scratchpad). When "
    "in doubt, prefer 'shared'. Return an empty list if nothing is worth saving."
)


def _extraction_cfg(agent: Agent) -> dict[str, Any]:
    cfg = agent.tools_config or {}
    if not isinstance(cfg, dict):
        return {}
    sub = cfg.get("extraction")
    return sub if isinstance(sub, dict) else {}


def _resolve_model(agent: Agent) -> str | None:
    sub = _extraction_cfg(agent)
    if not sub.get("enabled"):
        return None
    cfg = agent.tools_config or {}
    return (
        sub.get("model")
        or cfg.get("default_safety_model")
        or cfg.get("default_gate_model")
        or agent.model
        or None
    )


def _max_facts(agent: Agent) -> int:
    sub = _extraction_cfg(agent)
    n = sub.get("max_facts")
    if isinstance(n, int) and 1 <= n <= 20:
        return n
    return DEFAULT_MAX_FACTS


def _parse_json_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


async def _provider_for(db: AsyncSession, agent: Agent) -> LLMProvider | None:
    if not agent.llm_provider_id:
        return None
    return (await db.execute(
        select(LLMProvider).where(LLMProvider.id == agent.llm_provider_id)
    )).scalar_one_or_none()


async def _extract_facts(
    db: AsyncSession,
    agent: Agent,
    *,
    user_text: str,
    assistant_text: str,
) -> list[dict[str, Any]]:
    model = _resolve_model(agent)
    if not model:
        return []
    provider = await _provider_for(db, agent)
    if not provider:
        return []

    max_n = _max_facts(agent)
    user_payload = json.dumps(
        {
            "user": user_text[:2000],
            "assistant": assistant_text[:2000],
            "max_facts": max_n,
        },
        ensure_ascii=False,
    )

    res = await chat_completion(
        provider,
        model,
        [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_payload},
        ],
        max_tokens=EXTRACTION_MAX_TOKENS,
        timeout=EXTRACTION_TIMEOUT,
    )
    parsed = _parse_json_object((res.get("content") or "").strip()) or {}
    raw_facts = parsed.get("facts") or []
    if not isinstance(raw_facts, list):
        return []

    out: list[dict[str, Any]] = []
    for f in raw_facts[:max_n]:
        if not isinstance(f, dict):
            continue
        text = (f.get("text") or "").strip()
        if not text:
            continue
        visibility = f.get("visibility") if f.get("visibility") in ("private", "shared") else "private"
        tags = f.get("tags") if isinstance(f.get("tags"), list) else []
        tags = [str(t) for t in tags if t]
        out.append({"text": text, "visibility": visibility, "tags": tags})
    return out


async def _persist_fact(
    db: AsyncSession,
    agent: Agent,
    *,
    fact: str,
    visibility: str,
    tags: list[str],
    session_id: int | None,
) -> None:
    verdict = await gate_memory_write(db, agent=agent, fact=fact, visibility=visibility)
    if not verdict["save"]:
        return

    pii = await safety_pii(db, agent=agent, text=fact, phase="memory_write")
    text = pii["text"] if pii["redacted"] else fact

    try:
        await mem_service.store_memory(
            db,
            user_id=agent.user_id,
            agent_id=agent.id,
            fact=text,
            visibility=visibility,
            tags=tags,
            session_id=session_id,
        )
    except MemSvcError as e:
        log.warning("extraction store_memory failed: %s", e)


async def _run_extraction(
    agent_id: int,
    user_text: str,
    assistant_text: str,
    session_id: int | None,
) -> None:
    """Body of the background task — owns its own DB session."""
    if not user_text and not assistant_text:
        return
    try:
        async with async_session() as db:
            agent = (await db.execute(
                select(Agent).where(Agent.id == agent_id)
            )).scalar_one_or_none()
            if agent is None:
                return
            if not _resolve_model(agent):
                return

            try:
                facts = await _extract_facts(
                    db, agent, user_text=user_text, assistant_text=assistant_text
                )
            except Exception as e:  # noqa: BLE001
                log.warning("extraction LLM call failed for agent %s: %s", agent_id, e)
                return

            for f in facts:
                try:
                    await _persist_fact(
                        db,
                        agent,
                        fact=f["text"],
                        visibility=f["visibility"],
                        tags=f["tags"],
                        session_id=session_id,
                    )
                except Exception as e:  # noqa: BLE001
                    log.warning("extraction persist failed for agent %s: %s", agent_id, e)
    except Exception as e:  # noqa: BLE001
        log.warning("extraction outer failure for agent %s: %s", agent_id, e)


def schedule_extraction(
    *,
    agent_id: int,
    user_text: str,
    assistant_text: str,
    session_id: int | None = None,
) -> None:
    """Fire-and-forget extraction task.

    Safe to call from inside a request handler — runs on the event loop and
    swallows any error so the caller's response is never delayed or broken.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(_run_extraction(agent_id, user_text, assistant_text, session_id))
