# NOTICE: This file is protected under RCF-PL
"""Self-Forging layers 2 & 3: golden set + evaluation harness.

Layer 1 (the signal) already exists: `tracing.py` captures agent turns into the
user's `agent_traces` collection and stamps a `reward`/`quality_label` — weak at
write time, overwritten by a strong human 👍/👎 (see `human_score`). This module
closes the loop:

  * **Layer 2 — golden set.** Freeze a snapshot of *labeled* traces into a
    separate `golden_traces` collection. A golden example is `{input, expected,
    reward}` — the frozen ground truth we measure against. Freezing (not querying
    live) means the benchmark doesn't drift as new traces arrive.

  * **Layer 3 — harness.** Replay each golden input through two models (a `base`
    model and the candidate `forged` model), score each reply against the frozen
    `expected` answer, and report `mean(base)`, `mean(forged)`, and the delta.
    That delta is the number ADR-0001 calls the "A/B base-vs-forged" result —
    the evidence that a forged model is actually better, not just different.

Everything is scoped to the user's own Mongo cluster (`get_mongo_db`). No vendor
exfiltration — the golden set lives in the customer's Atlas, same trust boundary
as the traces it's built from.

Doctrine (see the self-forging memory): accumulating *unlabeled* traces is not
training. Only `human_labeled` traces (or, optionally, the weak write-time score)
enter the golden set — otherwise the harness measures "did the loop not crash",
not "was the answer right".
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)

GOLDEN_COLLECTION = "golden_traces"
TRACE_COLLECTION = "agent_traces"

# Tokeniser for the overlap scorer: lowercase word characters.
_WORD = re.compile(r"[a-z0-9]+")
# Very common English tokens carry little signal; ignore them so the score
# reflects content overlap, not "both sentences contain 'the'".
_STOPWORDS = frozenset(
    "a an the and or but is are was were be been being to of in on at for with "
    "this that these those it its as by from you i we they he she".split()
)


# ── scoring (pure, unit-testable) ────────────────────────────────────────────
# [RCF:PROTECTED]
def _tokens(text: str) -> set[str]:
    return {t for t in _WORD.findall((text or "").lower()) if t not in _STOPWORDS}


# [RCF:PROTECTED]
def score_response(expected: str, actual: str) -> float:
    """Similarity of a candidate reply to the expected answer, in [0.0, 1.0].

    A deliberately simple, dependency-free token-overlap (Jaccard) score — a
    proxy, not a judge. It rewards a reply that mentions the same content words
    as the golden answer. Good enough to detect a forged model regressing or
    improving in aggregate across many examples; not a per-example verdict.

    Both empty → 1.0 (nothing expected, nothing produced). One empty → 0.0.
    """
    exp, act = _tokens(expected), _tokens(actual)
    if not exp and not act:
        return 1.0
    if not exp or not act:
        return 0.0
    inter = len(exp & act)
    union = len(exp | act)
    return round(inter / union, 4)


# ── layer 2: golden set ──────────────────────────────────────────────────────
# [RCF:PROTECTED]
def _golden_query(min_reward: float, human_only: bool) -> dict[str, Any]:
    """Mongo filter selecting traces eligible for the golden set.

    We require a usable input and a non-empty expected answer, a reward at or
    above `min_reward`, and (by default) a human label — the strong signal.
    `reward is None` traces are intentionally excluded upstream and never match.
    """
    q: dict[str, Any] = {
        "reward": {"$gte": min_reward},
        "final_text": {"$nin": [None, ""]},
        "input_user_text": {"$nin": [None, ""]},
    }
    if human_only:
        q["human_labeled"] = True
    return q


# [RCF:PROTECTED]
async def select_labeled_traces(
    mdb,
    user_id: int,
    *,
    min_reward: float = 0.5,
    human_only: bool = True,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Return labeled traces for `user_id` eligible to seed the golden set."""
    cursor = mdb[TRACE_COLLECTION].find(
        {"user_id": user_id, **_golden_query(min_reward, human_only)},
        projection={
            "input_user_text": 1, "final_text": 1, "reward": 1,
            "quality_label": 1, "agent_id": 1, "model": 1,
            "human_labeled": 1, "created_at": 1,
        },
    ).sort("created_at", -1).limit(limit)
    return [doc async for doc in cursor]


# [RCF:PROTECTED]
def _to_golden(trace: dict[str, Any], user_id: int, frozen_at: datetime) -> dict[str, Any]:
    """Project a trace document into a frozen golden example."""
    return {
        "user_id": user_id,
        "source_trace_id": trace.get("_id"),
        "input": trace.get("input_user_text") or "",
        "expected": trace.get("final_text") or "",
        "reward": trace.get("reward"),
        "quality_label": trace.get("quality_label"),
        "agent_id": trace.get("agent_id"),
        "model": trace.get("model"),
        "human_labeled": bool(trace.get("human_labeled")),
        "frozen_at": frozen_at,
    }


# [RCF:PROTECTED]
async def freeze_golden_set(
    mdb,
    user_id: int,
    *,
    min_reward: float = 0.5,
    human_only: bool = True,
    limit: int = 500,
    replace: bool = True,
) -> dict[str, Any]:
    """Snapshot eligible traces into the `golden_traces` collection.

    `replace=True` clears this user's existing golden set first, so freezing is
    idempotent — re-running produces the current frozen set, not a growing pile
    of duplicates. Returns a summary the endpoint can echo back.
    """
    traces = await select_labeled_traces(
        mdb, user_id, min_reward=min_reward, human_only=human_only, limit=limit
    )
    frozen_at = datetime.now(timezone.utc)

    if replace:
        await mdb[GOLDEN_COLLECTION].delete_many({"user_id": user_id})

    examples = [_to_golden(t, user_id, frozen_at) for t in traces]
    if examples:
        await mdb[GOLDEN_COLLECTION].insert_many(examples)

    return {
        "frozen": len(examples),
        "frozen_at": frozen_at,
        "min_reward": min_reward,
        "human_only": human_only,
        "replaced": replace,
    }


# [RCF:PROTECTED]
async def get_golden_set(mdb, user_id: int, *, limit: int = 500) -> list[dict[str, Any]]:
    """Return the user's frozen golden examples (newest freeze first)."""
    cursor = mdb[GOLDEN_COLLECTION].find(
        {"user_id": user_id},
        projection={"input": 1, "expected": 1, "reward": 1, "model": 1,
                    "human_labeled": 1, "frozen_at": 1},
    ).sort("frozen_at", -1).limit(limit)
    return [doc async for doc in cursor]


# ── layer 3: harness ─────────────────────────────────────────────────────────
# [RCF:PROTECTED]
async def _reply_for(provider, model: str, system_prompt: str, user_input: str) -> str:
    """One-shot completion used by the harness. Isolated so a single failed
    example degrades to an empty reply (score 0) rather than aborting the run."""
    from app.services.llm_service import chat_completion

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_input})
    try:
        result = await chat_completion(provider, model, messages)
        return result.get("content") or ""
    except Exception as e:  # noqa: BLE001
        log.warning("harness completion failed (model=%s): %s", model, e)
        return ""


# [RCF:PROTECTED]
async def run_harness(
    mdb,
    user_id: int,
    *,
    base_provider,
    base_model: str,
    forged_provider,
    forged_model: str,
    system_prompt: str = "",
    limit: int = 100,
) -> dict[str, Any]:
    """Replay the golden set through base and forged models; report the delta.

    For each frozen example we generate a reply from both models and score each
    against the frozen `expected` answer. The headline number is
    `delta = mean(forged) - mean(base)`: positive means the forged model is, on
    this frozen benchmark, closer to the labeled-good answers than the base.

    Returns per-example rows plus aggregates. Does not persist — the caller
    decides whether to store the run.
    """
    golden = await get_golden_set(mdb, user_id, limit=limit)
    if not golden:
        return {
            "evaluated": 0,
            "base_model": base_model,
            "forged_model": forged_model,
            "mean_base": 0.0,
            "mean_forged": 0.0,
            "delta": 0.0,
            "message": "Golden set is empty — freeze it first via POST /forging/golden-set.",
            "examples": [],
        }

    rows: list[dict[str, Any]] = []
    for ex in golden:
        user_input = ex.get("input") or ""
        expected = ex.get("expected") or ""
        base_reply = await _reply_for(base_provider, base_model, system_prompt, user_input)
        forged_reply = await _reply_for(forged_provider, forged_model, system_prompt, user_input)
        base_s = score_response(expected, base_reply)
        forged_s = score_response(expected, forged_reply)
        rows.append({
            "input": user_input,
            "base_score": base_s,
            "forged_score": forged_s,
            "delta": round(forged_s - base_s, 4),
        })

    n = len(rows)
    mean_base = round(sum(r["base_score"] for r in rows) / n, 4)
    mean_forged = round(sum(r["forged_score"] for r in rows) / n, 4)
    return {
        "evaluated": n,
        "base_model": base_model,
        "forged_model": forged_model,
        "mean_base": mean_base,
        "mean_forged": mean_forged,
        "delta": round(mean_forged - mean_base, 4),
        "examples": rows,
    }
