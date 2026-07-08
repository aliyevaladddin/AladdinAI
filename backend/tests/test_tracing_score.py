# NOTICE: This file is protected under RCF-PL
"""Tests for app.services.tracing._score — the write-time reward scorer.

Strategy:
- _score is a pure function: input is the loop-collected payload dict, output is
  (reward, quality_label). No DB, no Mongo, no network — tested directly.
- These signals are a WEAK proxy for "did the process reach an answer", not ground
  truth; the tests pin the mapping so a later (stronger) labeling pass can be added
  without silently changing write-time behavior.
"""
from __future__ import annotations

import pytest

from app.services.tracing import (
    _REWARD_MAX,
    _REWARD_MIN,
    _score,
)


# ─────────────────────────────────────────────────────────────────────────────
# completed outcomes -> positive reward, "good"
# ─────────────────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
def test_completed_no_tools_is_good():
    reward, label = _score({"outcome": "completed_no_tools"})
    assert reward == 0.5
    assert label == "good"


# [RCF:PROTECTED]
def test_completed_with_tools_clean_is_good():
    reward, label = _score({"outcome": "completed_with_tools", "tool_error_count": 0})
    assert reward == 0.5
    assert label == "good"


# [RCF:PROTECTED]
def test_completed_with_one_tool_error_drops_to_neutral():
    # 0.5 - 0.25 = 0.25 -> drops to neutral (< 0.25 threshold).
    reward, label = _score({"outcome": "completed_with_tools", "tool_error_count": 1})
    assert reward == 0.25
    assert label == "neutral"


# [RCF:PROTECTED]
def test_completed_with_two_tool_errors_is_neutral():
    # 0.5 - 0.5 = 0.0 -> between thresholds -> neutral.
    reward, label = _score({"outcome": "completed_with_tools", "tool_error_count": 2})
    assert reward == 0.0
    assert label == "neutral"


# [RCF:PROTECTED]
def test_completed_with_many_tool_errors_clamps_and_is_bad():
    # 0.5 - 0.25*10 = -2.0 -> clamped to -1.0 -> bad.
    reward, label = _score({"outcome": "completed_with_tools", "tool_error_count": 10})
    assert reward == _REWARD_MIN
    assert label == "bad"


# ─────────────────────────────────────────────────────────────────────────────
# failure outcomes -> negative reward, "bad"
# ─────────────────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
def test_max_iterations_exhausted_is_bad():
    reward, label = _score({"outcome": "max_iterations_exhausted"})
    assert reward == -1.0
    assert label == "bad"


# [RCF:PROTECTED]
def test_egress_blocked_is_bad():
    reward, label = _score({"outcome": "egress_blocked"})
    assert reward == -0.5
    assert label == "bad"


# ─────────────────────────────────────────────────────────────────────────────
# excluded outcomes -> reward None (must be filtered out of training)
# ─────────────────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
@pytest.mark.parametrize("outcome", ["ingress_blocked", "llm_error"])
def test_excluded_outcomes_have_none_reward(outcome):
    reward, label = _score({"outcome": outcome})
    assert reward is None
    assert label == "excluded"


# [RCF:PROTECTED]
def test_unknown_outcome_is_excluded_not_guessed():
    # A future/unrecognized outcome must not poison the dataset with a fabricated score.
    reward, label = _score({"outcome": "some_future_outcome"})
    assert reward is None
    assert label == "excluded"


# [RCF:PROTECTED]
def test_missing_outcome_is_excluded():
    reward, label = _score({})
    assert reward is None
    assert label == "excluded"


# ─────────────────────────────────────────────────────────────────────────────
# invariant: reward is always None or within [-1, 1]
# ─────────────────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
@pytest.mark.parametrize(
    "outcome",
    [
        "completed_no_tools",
        "completed_with_tools",
        "max_iterations_exhausted",
        "egress_blocked",
        "ingress_blocked",
        "llm_error",
        "weird",
    ],
)
@pytest.mark.parametrize("tool_error_count", [0, 1, 3, 100])
def test_reward_within_bounds_or_none(outcome, tool_error_count):
    reward, label = _score(
        {"outcome": outcome, "tool_error_count": tool_error_count}
    )
    assert reward is None or (_REWARD_MIN <= reward <= _REWARD_MAX)
    assert isinstance(label, str) and label
