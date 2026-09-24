# NOTICE: This file is protected under RCF-PL
"""Tests for self-forging layers 2 & 3 (golden set + harness)."""
import json
from datetime import datetime, timezone

import pytest

from app.services.forging import (
    _assign_split,
    _golden_query,
    _split_group_key,
    _to_golden,
    export_golden_set,
    freeze_golden_set,
    get_golden_set,
    get_latest_ready_version,
    run_harness,
    score_response,
)


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
    assert score_response("the invoice is ready", "invoice ready") == 1.0


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
        "human_labeled": True, "session_id": "sess-42",
    }
    g = _to_golden(
        trace,
        user_id=42,
        frozen_at=frozen_at,
        dataset_version=1,
        split="train",
        split_group_key="session:sess-42",
    )
    assert g["user_id"] == 42
    assert g["source_trace_id"] == "abc"
    assert g["session_id"] == "sess-42"
    assert g["input"] == "how many orders?"
    assert g["expected"] == "you have 3 orders"
    assert g["reward"] == 1.0
    assert g["human_labeled"] is True
    assert g["dataset_version"] == 1
    assert g["split"] == "train"
    assert g["split_group_key"] == "session:sess-42"


class _FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    def sort(self, sort_spec, direction=None):
        if isinstance(sort_spec, list):
            for field, order in reversed(sort_spec):
                self._docs.sort(key=lambda d: d.get(field) or 0, reverse=(order == -1))
        elif isinstance(sort_spec, str):
            order = direction if direction is not None else 1
            self._docs.sort(key=lambda d: d.get(sort_spec) or 0, reverse=(order == -1))
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
        def match(d):
            for k, v in query.items():
                if k == "user_id" and d.get("user_id") != v:
                    return False
                if k == "dataset_version" and d.get("dataset_version") != v:
                    return False
                if k == "split" and d.get("split") != v:
                    return False
                if k == "status" and d.get("status") != v:
                    return False
                if k == "reward" and isinstance(v, dict):
                    if d.get("reward") is None:
                        return False
                    if "$gte" in v and d["reward"] < v["$gte"]:
                        return False
                    if "$lte" in v and d["reward"] > v["$lte"]:
                        return False
                if k == "human_labeled" and d.get("human_labeled") is not v:
                    return False
                if k in ("final_text", "input_user_text") and isinstance(v, dict) and d.get(k) in v["$nin"]:
                    return False
            return True
        return _FakeCursor([d for d in self.docs if match(d)])

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def update_one(self, query, update):
        for d in self.docs:
            if all(d.get(k) == v for k, v in query.items()):
                if "$set" in update:
                    d.update(update["$set"])
                break

    async def insert_many(self, docs):
        self.docs.extend([dict(d) for d in docs])


class _FakeMongo:
    def __init__(self, traces=None):
        self._c = {
            "agent_traces": _FakeCollection(traces or []),
            "golden_traces": _FakeCollection(),
            "dataset_versions": _FakeCollection(),
        }

    def __getitem__(self, name):
        return self._c[name]


@pytest.mark.asyncio
async def test_freeze_creates_incrementing_versions():
    traces = [
        {"_id": 1, "user_id": 1, "input_user_text": "q1", "final_text": "a1", "reward": 1.0, "human_labeled": True, "session_id": "s1"}
    ]
    mdb = _FakeMongo(traces)

    res1 = await freeze_golden_set(mdb, user_id=1)
    assert res1["version"] == 1
    assert len(mdb["dataset_versions"].docs) == 1

    res2 = await freeze_golden_set(mdb, user_id=1)
    assert res2["version"] == 2
    assert len(mdb["dataset_versions"].docs) == 2

    res_u2 = await freeze_golden_set(mdb, user_id=2)
    assert res_u2["version"] == 1


@pytest.mark.asyncio
async def test_freeze_small_dataset_falls_back_to_all_train():
    traces = [
        {"_id": i, "user_id": 1, "input_user_text": f"q{i}", "final_text": f"a{i}", "reward": 1.0, "human_labeled": True, "session_id": f"s{i}"}
        for i in range(4)
    ]
    mdb = _FakeMongo(traces)
    res = await freeze_golden_set(mdb, user_id=1)

    assert res["counts"]["train"] == 4
    assert res["counts"]["validation"] == 0
    assert res["counts"]["heldout"] == 0
    assert len(res["warnings"]) > 0

    docs = mdb["golden_traces"].docs
    assert all(d["split"] == "train" for d in docs)


@pytest.mark.asyncio
async def test_get_golden_set_defaults_to_latest_ready():
    traces_v1 = [
        {"_id": 1, "user_id": 1, "input_user_text": "old", "final_text": "old_ans", "reward": 1.0, "human_labeled": True}
    ]
    mdb = _FakeMongo(traces_v1)
    await freeze_golden_set(mdb, user_id=1)

    mdb["agent_traces"].docs.append(
        {"_id": 2, "user_id": 1, "input_user_text": "new", "final_text": "new_ans", "reward": 1.0, "human_labeled": True}
    )
    await freeze_golden_set(mdb, user_id=1)

    latest = await get_latest_ready_version(mdb, user_id=1)
    assert latest["version"] == 2

    items = await get_golden_set(mdb, user_id=1)
    assert all(it["dataset_version"] == 2 for it in items)


@pytest.mark.asyncio
async def test_export_golden_set_defaults_to_train_and_jsonl():
    traces = [
        {"_id": 1, "user_id": 1, "input_user_text": "hello", "final_text": "world", "reward": 1.0, "human_labeled": True}
    ]
    mdb = _FakeMongo(traces)
    await freeze_golden_set(mdb, user_id=1)

    out = await export_golden_set(mdb, user_id=1, fmt="sft")
    assert out["split"] == "train"
    assert out["examples"] == 1
    row = json.loads(out["jsonl"])
    assert row["prompt"] == "hello"
    assert row["completion"] == "world"


@pytest.mark.asyncio
async def test_dpo_pairing_strict_session_isolation():
    # sess-1 has both good and bad answers -> pairs!
    # sess-2 has bad answer with same prompt -> must NOT pair with sess-3!
    traces = [
        {"_id": 1, "user_id": 1, "session_id": "sess-1", "input_user_text": "help me", "final_text": "good reply", "reward": 1.0, "human_labeled": True},
        {"_id": 2, "user_id": 1, "session_id": "sess-1", "input_user_text": "help me", "final_text": "bad reply", "reward": -1.0, "human_labeled": True},
        {"_id": 3, "user_id": 1, "session_id": "sess-3", "input_user_text": "cross prompt", "final_text": "good cross", "reward": 1.0, "human_labeled": True},
        {"_id": 4, "user_id": 1, "session_id": "sess-2", "input_user_text": "cross prompt", "final_text": "bad cross", "reward": -1.0, "human_labeled": True},
    ]
    mdb = _FakeMongo(traces)
    await freeze_golden_set(mdb, user_id=1)

    out = await export_golden_set(mdb, user_id=1, fmt="dpo")
    assert out["examples"] == 1  # Only sess-1 paired!
    assert out["skipped_unpaired"] == 1  # sess-3 was skipped because sess-2 is a different session!
    row = json.loads(out["jsonl"])
    assert row["chosen_response"] == "good reply"
    assert row["rejected_response"] == "bad reply"


@pytest.mark.asyncio
async def test_harness_empty_heldout_not_evaluable():
    traces = [
        {"_id": 1, "user_id": 1, "input_user_text": "q1", "final_text": "a1", "reward": 1.0, "human_labeled": True},
        {"_id": 2, "user_id": 1, "input_user_text": "q2", "final_text": "a2", "reward": 1.0, "human_labeled": True},
    ]
    mdb = _FakeMongo(traces)
    await freeze_golden_set(mdb, user_id=1)

    result = await run_harness(
        mdb, user_id=1,
        base_provider=None, base_model="base",
        forged_provider=None, forged_model="forged",
    )
    assert result["evaluated"] == 0
    assert "not evaluable" in result["message"].lower()


def test_split_group_key_session_precedence():
    trace_a = {"session_id": "sess-1", "input": "hello"}
    trace_b = {"session_id": "sess-1", "input": "different question"}
    assert _split_group_key(trace_a) == "session:sess-1"
    assert _split_group_key(trace_a) == _split_group_key(trace_b)


def test_split_group_key_fallback_prompt_hash():
    trace_no_sess = {"session_id": None, "input": "hello"}
    trace_no_sess_same = {"input": "hello"}
    assert _split_group_key(trace_no_sess).startswith("prompt:")
    assert _split_group_key(trace_no_sess) == _split_group_key(trace_no_sess_same)


def test_split_group_key_distinct_sessions_different_keys():
    t1 = {"session_id": "sess-1", "input": "identical prompt"}
    t2 = {"session_id": "sess-2", "input": "identical prompt"}
    assert _split_group_key(t1) != _split_group_key(t2)


def test_assign_split_deterministic():
    key = "session:test-session"
    res1 = _assign_split(key)
    res2 = _assign_split(key)
    assert res1 == res2
    assert res1 in ("train", "validation", "heldout")


def test_assign_split_invalid_ratios():
    with pytest.raises(ValueError, match="Invalid split ratios"):
        _assign_split("session:1", {"train": 0.5, "validation": 0.1, "heldout": 0.1})