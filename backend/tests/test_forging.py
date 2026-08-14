# NOTICE: This file is protected under RCF-PL
"""Tests for self-forging layers 2 & 3 (golden set + harness).

The scoring and query-building are pure and covered directly. The Mongo-backed
freeze/harness paths need a per-user cluster the test harness doesn't configure,
so we test them against a tiny in-memory fake Mongo collection instead of the
real driver — enough to prove selection, freezing (idempotent replace), and the
base-vs-forged delta wiring.
"""
import json
from datetime import datetime, timezone

import pytest

from app.services.forging import (
    _golden_query,
    _to_golden,
    export_golden_set,
    freeze_golden_set,
    run_harness,
    score_response,
)


# ── score_response (pure) ────────────────────────────────────────────────────
def test_score_identical_is_one():
    assert score_response("ship the order today", "ship the order today") == 1.0


def test_score_disjoint_is_zero():
    assert score_response("shipping logistics", "quantum photosynthesis") == 0.0


def test_score_both_empty_is_one():
    assert score_response("", "") == 1.0


def test_score_one_empty_is_zero():
    assert score_response("something", "") == 0.0
    assert score_response("", "something") == 0.0


def test_score_partial_overlap_between_zero_and_one():
    s = score_response("the order shipped to the customer", "order shipped late")
    assert 0.0 < s < 1.0


def test_score_ignores_stopwords():
    # Differing only in stopwords → full content overlap → 1.0
    assert score_response("the invoice is ready", "invoice ready") == 1.0


# ── golden query builder (pure) ──────────────────────────────────────────────
def test_golden_query_human_only():
    q = _golden_query(min_reward=0.5, human_only=True)
    assert q["reward"] == {"$gte": 0.5}
    assert q["human_labeled"] is True
    assert q["final_text"] == {"$nin": [None, ""]}


def test_golden_query_without_human_filter():
    q = _golden_query(min_reward=0.0, human_only=False)
    assert "human_labeled" not in q
    assert q["reward"] == {"$gte": 0.0}


def test_to_golden_projects_fields():
    frozen_at = datetime.now(timezone.utc)
    trace = {
        "_id": "abc", "input_user_text": "how many orders?",
        "final_text": "you have 3 orders", "reward": 1.0,
        "quality_label": "good", "agent_id": 7, "model": "m",
        "human_labeled": True,
    }
    g = _to_golden(trace, user_id=42, frozen_at=frozen_at)
    assert g["user_id"] == 42
    assert g["source_trace_id"] == "abc"
    assert g["input"] == "how many orders?"
    assert g["expected"] == "you have 3 orders"
    assert g["reward"] == 1.0
    assert g["human_labeled"] is True


# ── fake Mongo for the async collection surface we use ───────────────────────
class _FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    def sort(self, *a, **k):
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    def __aiter__(self):
        async def gen():
            for d in self._docs:
                yield d
        return gen()


class _FakeCollection:
    def __init__(self, docs=None):
        self.docs = docs or []

    def find(self, query, projection=None):
        # Support the filters freeze/select actually issue.
        def match(d):
            for k, v in query.items():
                if k == "user_id" and d.get("user_id") != v:
                    return False
                if k == "reward" and isinstance(v, dict):
                    if d.get("reward") is None:
                        return False
                    if "$gte" in v and d["reward"] < v["$gte"]:
                        return False
                    # The DPO export selects rejected answers by an upper bound.
                    if "$lte" in v and d["reward"] > v["$lte"]:
                        return False
                if k == "human_labeled" and d.get("human_labeled") is not v:
                    return False
                if k in ("final_text", "input_user_text") and isinstance(v, dict) and d.get(k) in v["$nin"]:
                    return False
            return True
        return _FakeCursor([d for d in self.docs if match(d)])

    async def delete_many(self, query):
        uid = query.get("user_id")
        before = len(self.docs)
        self.docs = [d for d in self.docs if d.get("user_id") != uid]
        return type("R", (), {"deleted_count": before - len(self.docs)})()

    async def insert_many(self, docs):
        self.docs.extend(docs)


class _FakeMongo:
    def __init__(self, traces=None):
        self._c = {"agent_traces": _FakeCollection(traces or []), "golden_traces": _FakeCollection()}

    def __getitem__(self, name):
        return self._c[name]


# ── freeze_golden_set (fake Mongo) ───────────────────────────────────────────
@pytest.mark.asyncio
async def test_freeze_selects_only_eligible():
    traces = [
        {"_id": 1, "user_id": 1, "input_user_text": "q1", "final_text": "a1",
         "reward": 1.0, "human_labeled": True},
        {"_id": 2, "user_id": 1, "input_user_text": "q2", "final_text": "a2",
         "reward": 0.5, "human_labeled": False},  # not human-labeled → excluded
        {"_id": 3, "user_id": 1, "input_user_text": "q3", "final_text": "a3",
         "reward": -1.0, "human_labeled": True},   # reward too low → excluded
        {"_id": 4, "user_id": 2, "input_user_text": "q4", "final_text": "a4",
         "reward": 1.0, "human_labeled": True},     # other user → excluded
    ]
    mdb = _FakeMongo(traces)
    summary = await freeze_golden_set(mdb, user_id=1, min_reward=0.5, human_only=True)
    assert summary["frozen"] == 1
    assert len(mdb["golden_traces"].docs) == 1
    assert mdb["golden_traces"].docs[0]["input"] == "q1"


@pytest.mark.asyncio
async def test_freeze_is_idempotent_replace():
    traces = [{"_id": 1, "user_id": 1, "input_user_text": "q", "final_text": "a",
               "reward": 1.0, "human_labeled": True}]
    mdb = _FakeMongo(traces)
    await freeze_golden_set(mdb, user_id=1)
    await freeze_golden_set(mdb, user_id=1)  # second run must replace, not stack
    assert len(mdb["golden_traces"].docs) == 1


# ── run_harness (fake Mongo + stubbed model replies) ─────────────────────────
@pytest.mark.asyncio
async def test_harness_empty_golden_set():
    mdb = _FakeMongo([])
    result = await run_harness(
        mdb, user_id=1,
        base_provider=None, base_model="base",
        forged_provider=None, forged_model="forged",
    )
    assert result["evaluated"] == 0
    assert "empty" in result["message"].lower()


@pytest.mark.asyncio
async def test_harness_reports_delta(monkeypatch):
    # Freeze one golden example whose expected answer is "ship the order".
    traces = [{"_id": 1, "user_id": 1, "input_user_text": "what to do?",
               "final_text": "ship the order", "reward": 1.0, "human_labeled": True}]
    mdb = _FakeMongo(traces)
    await freeze_golden_set(mdb, user_id=1)

    # Stub the two models: forged nails the expected answer, base misses.
    async def fake_reply(provider, model, system_prompt, user_input):
        return "ship the order" if model == "forged" else "no idea"

    monkeypatch.setattr("app.services.forging._reply_for", fake_reply)

    result = await run_harness(
        mdb, user_id=1,
        base_provider=None, base_model="base",
        forged_provider=None, forged_model="forged",
    )
    assert result["evaluated"] == 1
    assert result["mean_forged"] == 1.0
    assert result["mean_base"] == 0.0
    assert result["delta"] == 1.0


# ── export_golden_set (fake Mongo) ───────────────────────────────────────────
# [RCF:PROTECTED]
def _labeled(_id, user_id, q, a, reward=1.0):
    return {"_id": _id, "user_id": user_id, "input_user_text": q,
            "final_text": a, "reward": reward, "human_labeled": True}


@pytest.mark.asyncio
async def test_export_sft_emits_prompt_completion():
    """SFT rows carry exactly the two keys Customizer reads for that type."""
    mdb = _FakeMongo([_labeled(1, 1, "what to do?", "ship the order")])
    await freeze_golden_set(mdb, user_id=1)

    out = await export_golden_set(mdb, 1, fmt="sft")

    assert out["examples"] == 1
    row = json.loads(out["jsonl"])
    assert row == {"prompt": "what to do?", "completion": "ship the order"}


@pytest.mark.asyncio
async def test_export_is_jsonl_not_json_array():
    """One JSON document per line — a JSON array would be rejected by the trainer."""
    mdb = _FakeMongo([_labeled(1, 1, "q1", "a1"), _labeled(2, 1, "q2", "a2")])
    await freeze_golden_set(mdb, user_id=1)

    out = await export_golden_set(mdb, 1, fmt="sft")
    lines = out["jsonl"].splitlines()

    assert len(lines) == 2
    assert all(json.loads(line)["prompt"] for line in lines)


@pytest.mark.asyncio
async def test_export_chat_includes_system_prompt():
    """Chat rows keep role order and carry the system prompt when given."""
    mdb = _FakeMongo([_labeled(1, 1, "hi", "hello")])
    await freeze_golden_set(mdb, user_id=1)

    out = await export_golden_set(mdb, 1, fmt="chat", system_prompt="You are terse.")
    messages = json.loads(out["jsonl"])["messages"]

    assert [m["role"] for m in messages] == ["system", "user", "assistant"]
    assert messages[0]["content"] == "You are terse."
    assert messages[2]["content"] == "hello"


@pytest.mark.asyncio
async def test_export_chat_omits_empty_system_prompt():
    """No system prompt means no empty system turn in the training data."""
    mdb = _FakeMongo([_labeled(1, 1, "hi", "hello")])
    await freeze_golden_set(mdb, user_id=1)

    out = await export_golden_set(mdb, 1, fmt="chat")

    assert [m["role"] for m in json.loads(out["jsonl"])["messages"]] == ["user", "assistant"]


@pytest.mark.asyncio
async def test_export_dpo_pairs_chosen_with_rejected_for_same_input():
    """A preference pair must contrast two answers to the *same* prompt."""
    traces = [
        _labeled(1, 1, "how to greet?", "Hello, how may I help?", reward=1.0),
        _labeled(2, 1, "how to greet?", "yo", reward=-1.0),  # thumbs-down
    ]
    mdb = _FakeMongo(traces)
    await freeze_golden_set(mdb, user_id=1)

    out = await export_golden_set(mdb, 1, fmt="dpo")
    row = json.loads(out["jsonl"])

    assert out["examples"] == 1
    assert row["prompt"] == [{"role": "user", "content": "how to greet?"}]
    assert row["chosen_response"] == "Hello, how may I help?"
    assert row["rejected_response"] == "yo"


@pytest.mark.asyncio
async def test_export_dpo_skips_prompts_never_rated_badly():
    """Without a rejected counterpart there is no preference to learn.

    The count is reported rather than silently dropped: an export much smaller
    than the golden set is a fact about the labels, not a bug.
    """
    mdb = _FakeMongo([_labeled(1, 1, "only good", "great answer", reward=1.0)])
    await freeze_golden_set(mdb, user_id=1)

    out = await export_golden_set(mdb, 1, fmt="dpo")

    assert out["examples"] == 0
    assert out["skipped_unpaired"] == 1
    assert out["golden_available"] == 1


@pytest.mark.asyncio
async def test_export_empty_golden_set_is_empty_not_error():
    """Nothing frozen yet is a normal state, not a failure."""
    mdb = _FakeMongo([])

    out = await export_golden_set(mdb, 1, fmt="sft")

    assert out["examples"] == 0
    assert out["jsonl"] == ""


@pytest.mark.asyncio
async def test_export_rejects_unknown_format():
    """An unknown format must fail loudly, not silently produce the wrong schema."""
    mdb = _FakeMongo([])

    with pytest.raises(ValueError, match="Unknown export format"):
        await export_golden_set(mdb, 1, fmt="alpaca")


@pytest.mark.asyncio
async def test_export_scopes_to_the_calling_user():
    """One user's traces never leak into another's training data."""
    mdb = _FakeMongo([_labeled(1, 1, "mine", "a"), _labeled(2, 2, "theirs", "b")])
    await freeze_golden_set(mdb, user_id=1)
    await freeze_golden_set(mdb, user_id=2)

    out = await export_golden_set(mdb, 1, fmt="sft")

    assert out["examples"] == 1
    assert json.loads(out["jsonl"])["prompt"] == "mine"


@pytest.mark.asyncio
async def test_export_preserves_non_ascii():
    """Cyrillic must survive as text, not as \\uXXXX escapes."""
    mdb = _FakeMongo([_labeled(1, 1, "как дела?", "хорошо")])
    await freeze_golden_set(mdb, user_id=1)

    out = await export_golden_set(mdb, 1, fmt="sft")

    assert "хорошо" in out["jsonl"]
    assert json.loads(out["jsonl"])["completion"] == "хорошо"
