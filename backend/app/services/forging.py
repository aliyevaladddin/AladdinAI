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

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)

GOLDEN_COLLECTION = "golden_traces"
TRACE_COLLECTION = "agent_traces"
DATASET_VERSION_COLLECTION = "dataset_versions"

DEFAULT_SPLIT_RATIOS = {"train": 0.70, "validation": 0.15, "heldout": 0.15}
MIN_EXAMPLES_PER_SPLIT = 5
MAX_VERSION_ALLOCATION_RETRIES = 5

# Tokeniser for the overlap scorer: lowercase word characters.
_WORD = re.compile(r"[a-z0-9]+")
# Very common English tokens carry little signal; ignore them so the score
# reflects content overlap, not "both sentences contain 'the'".
_STOPWORDS = frozenset(
    "a an the and or but is are was were be been being to of in on at for with "
    "this that these those it its as by from you i we they he she".split()
)


# ── splitting & grouping (pure, unit-testable) ──────────────────────────────
# [RCF:PROTECTED]
def _split_group_key(trace: dict[str, Any]) -> str:
    """Return the deterministic group key for a trace.

    Session ID always takes absolute precedence over input prompt.
    """
    session_id = trace.get("session_id")
    if session_id is not None:
        return f"session:{session_id}"
    input_text = trace.get("input_user_text") or trace.get("input") or ""
    digest = hashlib.sha256(input_text.encode("utf-8")).hexdigest()
    return f"prompt:{digest}"


# [RCF:PROTECTED]
def _assign_split(group_key: str, ratios: dict[str, float] | None = None) -> str:
    """Deterministically assign a group key to a split using SHA-256."""
    if ratios is None:
        ratios = DEFAULT_SPLIT_RATIOS

    allowed_keys = {"train", "validation", "heldout"}
    if set(ratios.keys()) != allowed_keys:
        raise ValueError(f"Split ratios must contain exactly {allowed_keys}, got {set(ratios.keys())}")

    train_r = ratios.get("train", 0.0)
    val_r = ratios.get("validation", 0.0)
    heldout_r = ratios.get("heldout", 0.0)
    total = train_r + val_r + heldout_r

    if abs(total - 1.0) > 1e-6 or any(r < 0 for r in (train_r, val_r, heldout_r)):
        raise ValueError(f"Invalid split ratios: {ratios}")

    digest = hashlib.sha256(group_key.encode("utf-8")).hexdigest()
    val = int(digest, 16) / (2**256)

    if val < train_r:
        return "train"
    elif val < train_r + val_r:
        return "validation"
    return "heldout"


# ── scoring (pure, unit-testable) ────────────────────────────────────────────
# [RCF:PROTECTED]
def _tokens(text: str) -> set[str]:
    return {t for t in _WORD.findall((text or "").lower()) if t not in _STOPWORDS}


# [RCF:PROTECTED]
def score_response(expected: str, actual: str) -> float:
    """Similarity of a candidate reply to the expected answer, in [0.0, 1.0]."""
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
    """Mongo filter selecting traces eligible for the golden set."""
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
            "human_labeled": 1, "created_at": 1, "session_id": 1,
        },
    ).sort([("created_at", -1), ("_id", -1)]).limit(limit)
    return [doc async for doc in cursor]


# [RCF:PROTECTED]
def _to_golden(
    trace: dict[str, Any],
    user_id: int,
    frozen_at: datetime,
    dataset_version: int,
    split: str,
    split_group_key: str,
    rejected_response: str | None = None,
    dpo_pair_status: str = "unpaired",
) -> dict[str, Any]:
    """Project a trace document into an immutable frozen golden example."""
    return {
        "user_id": user_id,
        "source_trace_id": trace.get("_id"),
        "session_id": trace.get("session_id"),
        "input": trace.get("input_user_text") or trace.get("input") or "",
        "expected": trace.get("final_text") or trace.get("expected") or "",
        "rejected_response": rejected_response,
        "dpo_pair_status": dpo_pair_status,
        "reward": trace.get("reward"),
        "quality_label": trace.get("quality_label"),
        "agent_id": trace.get("agent_id"),
        "model": trace.get("model"),
        "human_labeled": bool(trace.get("human_labeled")),
        "dataset_version": dataset_version,
        "split": split,
        "split_group_key": split_group_key,
        "frozen_at": frozen_at,
    }


# [RCF:PROTECTED]
async def get_latest_ready_version(mdb, user_id: int) -> dict[str, Any] | None:
    """Return the latest ready dataset version metadata for user_id."""
    cursor = mdb[DATASET_VERSION_COLLECTION].find(
        {"user_id": user_id, "status": "ready"}
    ).sort("version", -1).limit(1)
    docs = [d async for d in cursor]
    return docs[0] if docs else None


# [RCF:PROTECTED]
async def _resolve_dataset_version(mdb, user_id: int, version: int | None) -> int | None:
    """Resolve an explicit version or retrieve the latest ready version number."""
    if version is not None:
        return version
    latest = await get_latest_ready_version(mdb, user_id)
    return latest["version"] if latest else None


REJECTED_MAX_REWARD = -0.5


# [RCF:PROTECTED]
async def _fetch_rejected_traces(mdb, user_id: int, limit: int = 1000) -> list[dict[str, Any]]:
    """Fetch candidates for rejected responses."""
    cursor = mdb[TRACE_COLLECTION].find(
        {
            "user_id": user_id,
            "human_labeled": True,
            "reward": {"$lte": REJECTED_MAX_REWARD},
            "final_text": {"$nin": [None, ""]},
            "input_user_text": {"$nin": [None, ""]},
        },
        projection={"input_user_text": 1, "final_text": 1, "session_id": 1, "created_at": 1},
    ).sort([("created_at", -1), ("_id", -1)]).limit(limit)
    return [d async for d in cursor]


# [RCF:PROTECTED]
async def _ensure_forging_indexes(mdb) -> None:
    """Ensure unique and look-up indexes exist on dataset collections."""
    if hasattr(mdb[DATASET_VERSION_COLLECTION], "create_index"):
        await mdb[DATASET_VERSION_COLLECTION].create_index([("user_id", 1), ("version", 1)], unique=True)
        await mdb[DATASET_VERSION_COLLECTION].create_index([("user_id", 1), ("frozen_at", -1)])
    if hasattr(mdb[GOLDEN_COLLECTION], "create_index"):
        await mdb[GOLDEN_COLLECTION].create_index([("user_id", 1), ("dataset_version", 1), ("split", 1)])
        await mdb[GOLDEN_COLLECTION].create_index([("user_id", 1), ("split_group_key", 1)])


# [RCF:PROTECTED]
async def _reserve_next_version(mdb, user_id: int, base_manifest: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """Reserve a unique version by inserting a building manifest with retry on collision."""
    await _ensure_forging_indexes(mdb)
    for _ in range(MAX_VERSION_ALLOCATION_RETRIES):
        cursor = mdb[DATASET_VERSION_COLLECTION].find({"user_id": user_id}).sort("version", -1).limit(1)
        existing = [d async for d in cursor]
        candidate_version = (int(existing[0].get("version", 0)) + 1) if existing else 1

        manifest = dict(base_manifest)
        manifest["user_id"] = user_id
        manifest["version"] = candidate_version
        manifest["status"] = "building"

        try:
            await mdb[DATASET_VERSION_COLLECTION].insert_one(manifest)
            return candidate_version, manifest
        except Exception as e:
            if "duplicate" in str(e).lower() or "11000" in str(e):
                continue
            raise
    raise RuntimeError(f"Could not allocate dataset version for user {user_id} after {MAX_VERSION_ALLOCATION_RETRIES} attempts.")


# [RCF:PROTECTED]
async def freeze_golden_set(
    mdb,
    user_id: int,
    *,
    min_reward: float = 0.5,
    human_only: bool = True,
    limit: int = 500,
    ratios: dict[str, float] | None = None,
    replace: bool = False,
) -> dict[str, Any]:
    """Snapshot eligible traces into a new immutable dataset version."""
    if ratios is None:
        ratios = DEFAULT_SPLIT_RATIOS

    traces = await select_labeled_traces(
        mdb, user_id, min_reward=min_reward, human_only=human_only, limit=limit
    )
    rejected_traces = await _fetch_rejected_traces(mdb, user_id, limit=limit * 2)
    frozen_at = datetime.now(timezone.utc)

    # 1. Deterministic grouping & tentative split assignment
    group_splits: dict[str, str] = {}
    staged_items: list[tuple[dict[str, Any], str, str, str | None, str]] = []

    for t in traces:
        gkey = _split_group_key(t)
        if gkey not in group_splits:
            group_splits[gkey] = _assign_split(gkey, ratios)
        split = group_splits[gkey]

        user_input = t.get("input_user_text") or t.get("input") or ""
        sess_id = t.get("session_id")

        same_input_candidates = [
            r for r in rejected_traces
            if (r.get("input_user_text") or r.get("input")) == user_input
        ]

        matched_rej = None
        dpo_status = "unpaired"

        if same_input_candidates:
            if sess_id is not None:
                same_session_match = next((r for r in same_input_candidates if r.get("session_id") == sess_id), None)
                if same_session_match is not None:
                    dpo_status = "paired"
                    matched_rej = same_session_match.get("final_text")
                else:
                    dpo_status = "cross_session"
            else:
                dpo_status = "cross_session"

        staged_items.append((t, split, gkey, matched_rej, dpo_status))

    counts = {"train": 0, "validation": 0, "heldout": 0}
    for _, split, _, _, _ in staged_items:
        counts[split] = counts.get(split, 0) + 1

    warnings: list[str] = []
    if len(staged_items) > 0 and any(counts[s] < MIN_EXAMPLES_PER_SPLIT for s in ("train", "validation", "heldout")):
        warnings.append(
            f"One or more splits had fewer than {MIN_EXAMPLES_PER_SPLIT} examples; "
            "falling back to assigning all examples to train."
        )
        staged_items = [(t, "train", gkey, rej, status) for (t, _, gkey, rej, status) in staged_items]
        counts = {"train": len(staged_items), "validation": 0, "heldout": 0}

    # 2. Concurrency-safe version allocation
    base_manifest = {
        "counts": counts,
        "ratios": ratios,
        "split_strategy": "session",
        "min_reward": min_reward,
        "human_only": human_only,
        "total_examples": len(staged_items),
        "frozen_at": frozen_at,
        "warnings": warnings,
    }

    version, manifest = await _reserve_next_version(mdb, user_id, base_manifest)

    try:
        examples = [
            _to_golden(t, user_id, frozen_at, version, split, gkey, rej, status)
            for (t, split, gkey, rej, status) in staged_items
        ]
        if examples:
            await mdb[GOLDEN_COLLECTION].insert_many(examples)

        manifest["status"] = "ready"
        if hasattr(mdb[DATASET_VERSION_COLLECTION], "update_one"):
            await mdb[DATASET_VERSION_COLLECTION].update_one(
                {"user_id": user_id, "version": version},
                {"$set": {"status": "ready"}},
            )
    except Exception:
        manifest["status"] = "failed"
        if hasattr(mdb[DATASET_VERSION_COLLECTION], "update_one"):
            await mdb[DATASET_VERSION_COLLECTION].update_one(
                {"user_id": user_id, "version": version},
                {"$set": {"status": "failed"}},
            )
        raise

    return {
        "version": version,
        "frozen": len(staged_items),
        "counts": counts,
        "status": "ready",
        "frozen_at": frozen_at,
        "min_reward": min_reward,
        "human_only": human_only,
        "replaced": replace,
        "warnings": warnings,
    }


# [RCF:PROTECTED]
async def get_golden_set(
    mdb,
    user_id: int,
    *,
    version: int | None = None,
    split: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Return frozen golden examples for user_id (defaults to latest ready version)."""
    resolved_version = await _resolve_dataset_version(mdb, user_id, version)
    if resolved_version is None:
        return []

    query: dict[str, Any] = {"user_id": user_id, "dataset_version": resolved_version}
    if split is not None:
        query["split"] = split

    cursor = mdb[GOLDEN_COLLECTION].find(
        query,
        projection={
            "input": 1, "expected": 1, "rejected_response": 1, "dpo_pair_status": 1,
            "reward": 1, "model": 1, "human_labeled": 1, "frozen_at": 1,
            "dataset_version": 1, "split": 1, "session_id": 1, "split_group_key": 1,
        },
    ).sort([("frozen_at", -1), ("_id", -1)]).limit(limit)
    return [doc async for doc in cursor]


# ── layer 2b: export for training ────────────────────────────────────────────
EXPORT_FORMATS = ("sft", "chat", "dpo")


# [RCF:PROTECTED]
def _sft_row(ex: dict[str, Any]) -> dict[str, Any]:
    return {"prompt": ex.get("input") or "", "completion": ex.get("expected") or ""}


# [RCF:PROTECTED]
def _chat_row(ex: dict[str, Any], system_prompt: str) -> dict[str, Any]:
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": ex.get("input") or ""})
    messages.append({"role": "assistant", "content": ex.get("expected") or ""})
    return {"messages": messages}


# [RCF:PROTECTED]
async def export_golden_set(
    mdb,
    user_id: int,
    *,
    version: int | None = None,
    split: str = "train",
    fmt: str = "sft",
    system_prompt: str = "",
    limit: int = 500,
) -> dict[str, Any]:
    """Render frozen golden set as JSONL lines ready for training."""
    if fmt not in EXPORT_FORMATS:
        raise ValueError(f"Unknown export format: {fmt!r} (expected one of {EXPORT_FORMATS})")

    resolved_version = await _resolve_dataset_version(mdb, user_id, version)
    golden = await get_golden_set(mdb, user_id, version=resolved_version, split=split, limit=limit)

    rows: list[dict[str, Any]] = []
    skipped_unpaired = 0
    skipped_cross_session = 0
    warnings: list[str] = []

    if fmt == "dpo":
        for ex in golden:
            user_input = ex.get("input") or ""
            status = ex.get("dpo_pair_status")
            counterpart = ex.get("rejected_response")

            if status == "paired" and counterpart:
                rows.append({
                    "prompt": [{"role": "user", "content": user_input}],
                    "chosen_response": ex.get("expected") or "",
                    "rejected_response": counterpart,
                })
            elif status == "cross_session":
                skipped_cross_session += 1
            else:
                skipped_unpaired += 1

        if skipped_cross_session > 0:
            warnings.append(f"{skipped_cross_session} DPO pairs skipped (cross-session)")
    else:
        for ex in golden:
            if not (ex.get("input") and ex.get("expected")):
                continue
            rows.append(
                _sft_row(ex) if fmt == "sft" else _chat_row(ex, system_prompt)
            )

    jsonl = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
    result: dict[str, Any] = {
        "format": fmt,
        "split": split,
        "dataset_version": resolved_version,
        "examples": len(rows),
        "golden_available": len(golden),
        "jsonl": jsonl,
        "warnings": warnings,
    }
    if fmt == "dpo":
        result["skipped_unpaired"] = skipped_unpaired
        result["skipped_cross_session"] = skipped_cross_session
    return result


# ── layer 3: harness ─────────────────────────────────────────────────────────
# [RCF:PROTECTED]
async def _reply_for(provider, model: str, system_prompt: str, user_input: str) -> str:
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
    version: int | None = None,
    split: str = "heldout",
    base_provider,
    base_model: str,
    forged_provider,
    forged_model: str,
    system_prompt: str = "",
    limit: int = 100,
) -> dict[str, Any]:
    """Replay golden set through base and forged models; defaults to `heldout` split."""
    resolved_version = await _resolve_dataset_version(mdb, user_id, version)
    golden = await get_golden_set(mdb, user_id, version=resolved_version, split=split, limit=limit)

    if not golden:
        return {
            "evaluated": 0,
            "split": split,
            "dataset_version": resolved_version,
            "base_model": base_model,
            "forged_model": forged_model,
            "mean_base": 0.0,
            "mean_forged": 0.0,
            "delta": 0.0,
            "message": f"Golden set ({split} split) has 0 examples — not evaluable.",
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
        "split": split,
        "dataset_version": resolved_version,
        "base_model": base_model,
        "forged_model": forged_model,
        "mean_base": mean_base,
        "mean_forged": mean_forged,
        "delta": round(mean_forged - mean_base, 4),
        "examples": rows,
    }