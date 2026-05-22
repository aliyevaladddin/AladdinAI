"""Apply user-defined routing rules to pick which agent handles an
incoming message.

Looks at `router_configs` rows where `is_active = true` for the user,
then walks them in id order. The first config that successfully picks an
agent wins. If none picks, the caller falls back to `channel.agent_id`.

Config shape (per `frontend/.../router/page.tsx`):

  type = "keyword" | "hybrid":
    {"rules": [{"keywords": ["price", "cost"], "agent_id": 5}, ...],
     "fallback_agent_id": 3}

  type = "llm_classifier":
    {"fallback_agent_id": 3,
     "agents": [{"id": 1, "name": "Sales", "role": "..."}, ...]}

`hybrid` runs keyword matching first; if nothing matches, it falls
through to llm_classifier with the same `agents` list (or the user's
agents if none provided).
"""
from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.llm_provider import LLMProvider
from app.models.router_config import RouterConfig
from app.services.llm_service import LLMError, chat_completion

log = logging.getLogger(__name__)


async def resolve_agent_id(
    db: AsyncSession,
    user_id: int,
    text: str,
    *,
    channel_agent_id: int | None = None,
) -> int | None:
    """Return the agent id to route this message to, or None to use the caller's default.

    `channel_agent_id` is informational — it lets us log overrides clearly.
    The caller still owns the fallback decision.
    """
    if not text:
        return None

    result = await db.execute(
        select(RouterConfig)
        .where(RouterConfig.user_id == user_id, RouterConfig.is_active == True)  # noqa: E712
        .order_by(RouterConfig.id)
    )
    configs = result.scalars().all()
    if not configs:
        return None

    for cfg in configs:
        picked = await _resolve_one(db, user_id, cfg, text)
        if picked is not None:
            if channel_agent_id is not None and picked != channel_agent_id:
                log.info(
                    "router: config %s (%s) overrode channel agent %s -> %s",
                    cfg.id, cfg.type, channel_agent_id, picked,
                )
            else:
                log.info("router: config %s (%s) picked agent %s", cfg.id, cfg.type, picked)
            return picked

    return None


async def _resolve_one(
    db: AsyncSession, user_id: int, cfg: RouterConfig, text: str
) -> int | None:
    """Apply a single router config to the text. Returns agent id or None."""
    config: dict[str, Any] = cfg.config or {}
    fallback = config.get("fallback_agent_id")

    if cfg.type == "keyword":
        picked = _match_keywords(config.get("rules") or [], text)
        return picked if picked is not None else fallback

    if cfg.type == "llm_classifier":
        picked = await _classify_with_llm(db, user_id, config, text, fallback_agent_id=fallback)
        return picked if picked is not None else fallback

    if cfg.type == "hybrid":
        picked = _match_keywords(config.get("rules") or [], text)
        if picked is not None:
            return picked
        picked = await _classify_with_llm(db, user_id, config, text, fallback_agent_id=fallback)
        return picked if picked is not None else fallback

    log.warning("router: unknown config type %r in config %s — skipping", cfg.type, cfg.id)
    return None


# ── keyword matching ────────────────────────────────────────────────

_WORD_RE = re.compile(r"\b\w+\b", re.UNICODE)


def _match_keywords(rules: list[dict], text: str) -> int | None:
    """Walk rules in order. First rule whose keyword appears in `text`
    (case-insensitive, substring match) wins. Empty rules are skipped.
    """
    lowered = text.lower()
    # token set for safer matching on short keywords (avoid "art" matching "start")
    tokens = set(m.group(0).lower() for m in _WORD_RE.finditer(text))

    for rule in rules:
        agent_id = rule.get("agent_id")
        keywords = rule.get("keywords") or []
        if not agent_id or not keywords:
            continue
        for kw in keywords:
            kw_lc = str(kw).strip().lower()
            if not kw_lc:
                continue
            # Multi-word keyword → substring; single word → token match
            if " " in kw_lc:
                if kw_lc in lowered:
                    return int(agent_id)
            else:
                if kw_lc in tokens:
                    return int(agent_id)
    return None


# ── LLM classifier ──────────────────────────────────────────────────

_CLASSIFIER_PROMPT = (
    "You are a routing classifier. Given a user message and a list of "
    "available agents, pick the single agent best suited to handle the "
    "message. Reply with ONLY the agent id as an integer (e.g. `7`). "
    "If none of the agents fits, reply with `none`."
)


async def _classify_with_llm(
    db: AsyncSession,
    user_id: int,
    config: dict[str, Any],
    text: str,
    *,
    fallback_agent_id: int | None,
) -> int | None:
    """Use an LLM to pick an agent id from the configured agent list.

    The classifier runs on the fallback agent's provider — the user has
    already configured that provider, so no extra setup is required. If no
    fallback agent exists, we can't pick a provider and skip the call.
    """
    agents_list = config.get("agents") or []
    if not agents_list:
        # Hybrid configs may omit `agents` — load the user's agents instead.
        result = await db.execute(select(Agent).where(Agent.user_id == user_id))
        agents = result.scalars().all()
        agents_list = [{"id": a.id, "name": a.name, "role": a.role} for a in agents]
    if not agents_list:
        log.warning("router: llm_classifier has no agents to choose from")
        return None

    if not fallback_agent_id:
        log.warning(
            "router: llm_classifier needs a fallback agent to borrow a provider — skipping"
        )
        return None

    fb_result = await db.execute(select(Agent).where(Agent.id == fallback_agent_id))
    fb_agent = fb_result.scalar_one_or_none()
    if not fb_agent or not fb_agent.llm_provider_id:
        log.warning("router: fallback agent %s has no llm_provider — skipping classifier",
                    fallback_agent_id)
        return None

    prov_result = await db.execute(
        select(LLMProvider).where(LLMProvider.id == fb_agent.llm_provider_id)
    )
    provider = prov_result.scalar_one_or_none()
    if not provider:
        log.warning("router: provider %s not found — skipping classifier",
                    fb_agent.llm_provider_id)
        return None

    options = "\n".join(
        f"- id={a.get('id')} name={a.get('name')!r} role={a.get('role')!r}"
        for a in agents_list
    )
    user_block = f"Available agents:\n{options}\n\nUser message:\n{text}\n\nAgent id:"

    try:
        resp = await chat_completion(
            provider,
            fb_agent.model,
            [
                {"role": "system", "content": _CLASSIFIER_PROMPT},
                {"role": "user", "content": user_block},
            ],
            max_tokens=16,
        )
    except LLMError as e:
        log.warning("router: classifier LLM call failed: %s", e)
        return None

    content = (resp.get("content") or "").strip().lower()
    if not content or content.startswith("none"):
        return None

    # Extract first integer in the reply
    m = re.search(r"\d+", content)
    if not m:
        log.debug("router: classifier reply has no integer: %r", content)
        return None
    picked = int(m.group(0))

    valid_ids = {int(a.get("id")) for a in agents_list if a.get("id") is not None}
    if picked not in valid_ids:
        log.warning("router: classifier picked unknown id %s (valid: %s)", picked, valid_ids)
        return None
    return picked
