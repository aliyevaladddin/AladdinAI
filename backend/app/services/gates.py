# NOTICE: This file is protected under RCF-PL
"""SLM gates — optional filters between agents and memory operations.

Three gates:
  - gate_handoff       — cleans context before delegate/ask_agent
  - gate_memory_write  — decides if a `remember` payload is worth saving
  - gate_recall_rerank — re-ranks vector-search results by semantic relevance

All gates are pass-through unless explicitly configured. Configuration lives
in `agent.tools_config.gates`:

    {
      "default_gate_model": "<nim model id>" | null,
      "gates": {
        "handoff":       { "enabled": true,  "model": "<nim model id>" },
        "memory_write":  { "enabled": false, "model": null },
        "recall_rerank": { "enabled": true,  "model": null }
      }
    }

Resolution order for the model: per-gate `model` -> `default_gate_model`.
If neither is set, the gate is pass-through regardless of `enabled`.

Provider: we reuse the agent's own `llm_provider_id` (typically NIM). If
the agent has no provider, gates are pass-through.

Fail-open: any error inside a gate returns the unfiltered input. Gates
must never crash the main flow.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.llm_provider import LLMProvider
from app.services import gate_log
from app.services.llm_service import LLMError, chat_completion

log = logging.getLogger(__name__)

PREVIEW_LEN = 400
GATE_TIMEOUT = 15.0
GATE_MAX_TOKENS = 512


# ─────────────────────────────────────────────────────────────────────────────
# Config helpers
# ─────────────────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
def _gates_config(agent: Agent) -> dict[str, Any]:
    cfg = agent.tools_config or {}
    if not isinstance(cfg, dict):
        return {}
    gates = cfg.get("gates")
    return gates if isinstance(gates, dict) else {}


# [RCF:PROTECTED]
def _resolve_model(agent: Agent, gate_name: str) -> str | None:
    cfg = agent.tools_config or {}
    if not isinstance(cfg, dict):
        return None
    per_gate = (cfg.get("gates") or {}).get(gate_name) or {}
    if not isinstance(per_gate, dict):
        return None
    if not per_gate.get("enabled"):
        return None
    return per_gate.get("model") or cfg.get("default_gate_model") or None


# [RCF:PROTECTED]
async def _provider_for(db: AsyncSession, agent: Agent) -> LLMProvider | None:
    if not agent.llm_provider_id:
        return None
    return (await db.execute(
        select(LLMProvider).where(LLMProvider.id == agent.llm_provider_id)
    )).scalar_one_or_none()


# [RCF:PROTECTED]
async def _call_slm(
    provider: LLMProvider,
    model: str,
    system: str,
    user: str,
) -> str:
    """Run a one-shot SLM call. Returns content or raises LLMError."""
    res = await chat_completion(
        provider,
        model,
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=GATE_MAX_TOKENS,
        timeout=GATE_TIMEOUT,
    )
    return (res.get("content") or "").strip()


# [RCF:PROTECTED]
def _parse_json_object(text: str) -> dict[str, Any] | None:
    """Extract the first JSON object from `text` (LLMs often wrap in prose)."""
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


# ─────────────────────────────────────────────────────────────────────────────
# Gate 1 — Handoff filter
# ─────────────────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
async def gate_handoff(
    db: AsyncSession,
    *,
    source_agent: Agent,
    target_agent: Agent,
    task: str,
    context: dict[str, Any] | None,
) -> dict[str, Any]:
    """Filter the handoff payload. Returns {task, context} (possibly trimmed).

    Pass-through if disabled or no model configured.
    """
    model = _resolve_model(source_agent, "handoff")
    if not model:
        return {"task": task, "context": context}

    provider = await _provider_for(db, source_agent)
    if not provider:
        return {"task": task, "context": context}

    started = time.monotonic()
    system = (
        "You are a context filter between AI agents. Strip irrelevant chatter, "
        "keep only what the target agent needs to act. Reply with strict JSON: "
        '{"task": "<refined task>", "context": <object or null>, "reason": "<short>"}.'
    )
    user_msg = json.dumps({
        "from_agent": {"name": source_agent.name, "role": source_agent.role},
        "to_agent": {"name": target_agent.name, "role": target_agent.role,
                     "system_prompt_excerpt": (target_agent.system_prompt or "")[:300]},
        "task": task,
        "context": context or {},
    }, ensure_ascii=False)

    try:
        raw = await _call_slm(provider, model, system, user_msg)
        parsed = _parse_json_object(raw)
        if not parsed:
            raise LLMError("Gate returned non-JSON")
        new_task = parsed.get("task") or task
        new_ctx = parsed.get("context") if isinstance(parsed.get("context"), dict) else context
        reason = (parsed.get("reason") or "")[:PREVIEW_LEN]

        await gate_log.record(
            db,
            user_id=source_agent.user_id,
            gate="handoff",
            agent_id=source_agent.id,
            model=model,
            decision="rerank",
            reason=reason,
            latency_ms=int((time.monotonic() - started) * 1000),
            input_preview=task[:PREVIEW_LEN],
            meta={"target_agent_id": target_agent.id},
        )
        return {"task": new_task, "context": new_ctx}
    except (LLMError, Exception) as e:  # noqa: BLE001
        log.warning("gate_handoff failed (passing through): %s", e)
        await gate_log.record(
            db,
            user_id=source_agent.user_id,
            gate="handoff",
            agent_id=source_agent.id,
            model=model,
            decision="pass",
            reason=f"gate_error: {e}"[:PREVIEW_LEN],
            latency_ms=int((time.monotonic() - started) * 1000),
            input_preview=task[:PREVIEW_LEN],
            meta={"target_agent_id": target_agent.id, "error": True},
        )
        return {"task": task, "context": context}


# ─────────────────────────────────────────────────────────────────────────────
# Gate 2 — Memory write classifier
# ─────────────────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
async def gate_memory_write(
    db: AsyncSession,
    *,
    agent: Agent,
    fact: str,
    visibility: str,
) -> dict[str, Any]:
    """Decide whether a fact is worth persisting.

    Returns {save: bool, reason: str}. Pass-through (save=True) if disabled.
    """
    model = _resolve_model(agent, "memory_write")
    if not model:
        return {"save": True, "reason": "gate_disabled"}

    provider = await _provider_for(db, agent)
    if not provider:
        return {"save": True, "reason": "no_provider"}

    started = time.monotonic()
    system = (
        "You decide if a fact is worth saving in long-term memory. Reject "
        "trivia, acknowledgements ('ok', 'thanks'), and ephemeral chatter. "
        "Accept names, preferences, decisions, deadlines, IDs, contact info. "
        'Reply with strict JSON: {"save": true|false, "reason": "<short>"}.'
    )
    user_msg = json.dumps({"fact": fact, "visibility": visibility}, ensure_ascii=False)

    try:
        raw = await _call_slm(provider, model, system, user_msg)
        parsed = _parse_json_object(raw) or {}
        save = bool(parsed.get("save", True))
        reason = (parsed.get("reason") or "")[:PREVIEW_LEN]
    except Exception as e:  # noqa: BLE001
        log.warning("gate_memory_write failed (saving anyway): %s", e)
        save, reason = True, f"gate_error: {e}"

    await gate_log.record(
        db,
        user_id=agent.user_id,
        gate="memory_write",
        agent_id=agent.id,
        model=model,
        decision="pass" if save else "block",
        reason=reason,
        latency_ms=int((time.monotonic() - started) * 1000),
        input_preview=fact[:PREVIEW_LEN],
        meta={"visibility": visibility},
    )
    return {"save": save, "reason": reason}


# ─────────────────────────────────────────────────────────────────────────────
# Gate 3 — Recall reranker
# ─────────────────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
async def gate_recall_rerank(
    db: AsyncSession,
    *,
    agent: Agent,
    query: str,
    results: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    """Reorder vector-search results by semantic relevance to `query`.

    Pass-through if disabled, fewer than 2 results, or on any failure.
    """
    if len(results) < 2:
        return results
    model = _resolve_model(agent, "recall_rerank")
    if not model:
        return results

    provider = await _provider_for(db, agent)
    if not provider:
        return results

    started = time.monotonic()
    system = (
        "You rerank memory snippets by relevance to a query. "
        "Reply with strict JSON: {\"order\": [<id>, <id>, ...], \"reason\": \"<short>\"}. "
        "Only include ids that appear in the input. Most relevant first."
    )
    user_msg = json.dumps({
        "query": query,
        "snippets": [{"id": r["id"], "fact": r.get("fact", "")} for r in results],
    }, ensure_ascii=False)

    try:
        raw = await _call_slm(provider, model, system, user_msg)
        parsed = _parse_json_object(raw) or {}
        order = parsed.get("order") or []
        if not isinstance(order, list):
            raise ValueError("order is not a list")

        by_id = {r["id"]: r for r in results}
        reranked = [by_id[oid] for oid in order if oid in by_id]
        # Append any missed results at the bottom to preserve recall.
        reranked.extend(r for r in results if r["id"] not in {x["id"] for x in reranked})
        out = reranked[:limit]

        await gate_log.record(
            db,
            user_id=agent.user_id,
            gate="recall_rerank",
            agent_id=agent.id,
            model=model,
            decision="rerank",
            reason=(parsed.get("reason") or "")[:PREVIEW_LEN],
            latency_ms=int((time.monotonic() - started) * 1000),
            input_preview=query[:PREVIEW_LEN],
            meta={"in_count": len(results), "out_count": len(out)},
        )
        return out
    except Exception as e:  # noqa: BLE001
        log.warning("gate_recall_rerank failed (passing through): %s", e)
        await gate_log.record(
            db,
            user_id=agent.user_id,
            gate="recall_rerank",
            agent_id=agent.id,
            model=model,
            decision="pass",
            reason=f"gate_error: {e}"[:PREVIEW_LEN],
            latency_ms=int((time.monotonic() - started) * 1000),
            input_preview=query[:PREVIEW_LEN],
            meta={"in_count": len(results), "error": True},
        )
        return results
