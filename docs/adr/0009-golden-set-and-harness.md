// NOTICE: This file is protected under RCF-PL
# ADR-0009: Golden Set + Evaluation Harness (Self-Forging Layers 2 & 3)

**Status**: Accepted

**Date**: 2026-07-14

**Deciders**: AladdinAI core

**Tags**: backend, self-forging, evaluation

## Context

ADR-0001 established Self-Forging: train a specialised CRM model from agent
traces. It listed "model evaluation metrics" and an "A/B testing framework
(base vs forged)" as future work. Layer 1 (the human 👍/👎 signal that stamps a
`reward` onto traces) shipped later. But the loop was still open at the top:

- There was no way to **freeze** a set of labeled traces as a stable benchmark.
- There was no way to **measure** whether a forged model beats the base model.

Without those two, "the forged model is better" is a belief, not a number. You
cannot filter traces into a benchmark, and you cannot run base-vs-forged.

## Decision

Add two layers as `app.services.forging` + `app.routers.forging`:

1. **Layer 2 — golden set.** `freeze_golden_set` selects traces with a usable
   input, a non-empty expected answer, and `reward >= min_reward` (human-labeled
   only by default), and snapshots them as `{input, expected, reward}` documents
   in a separate `golden_traces` collection in the **user's own Mongo**. Freezing
   is idempotent (replaces the prior set). A frozen benchmark does not drift as
   new traces arrive.

2. **Layer 3 — harness.** `run_harness` replays each golden input through a base
   model and a forged model, scores both replies against the frozen `expected`
   with `score_response`, and reports `mean_base`, `mean_forged`, and
   `delta = mean_forged - mean_base`.

3. **Scorer.** `score_response` is a pure, dependency-free token-overlap
   (Jaccard) proxy. It measures aggregate movement across many examples, not a
   per-reply verdict. It is one pure function, so a stronger scorer (embedding
   similarity, LLM judge) is a drop-in replacement.

4. **Edition gate.** Endpoints return `403` on the community edition, mirroring
   how trace capture defaults off there.

## Consequences

### Positive
- The self-forging loop is closed end to end: capture → label → freeze → measure.
- `delta` is a concrete, defensible number for "was the fine-tune worth it".
- All data stays in the customer's own Atlas — no vendor exfiltration.
- The scorer and selection logic are pure and unit-tested without Mongo.

### Negative
- Token-overlap is a weak proxy; a model can score well by keyword-matching
  without being genuinely better. Mitigated by treating it as an aggregate
  signal and keeping the scorer swappable.
- The harness makes 2 LLM calls per golden example — cost scales with set size
  (bounded by `limit`).

### Neutral
- `golden_traces` is a snapshot, deliberately decoupled from live `agent_traces`;
  re-freezing is a manual step.

## Alternatives Considered

### Alternative 1: Query traces live at eval time (no freeze)
- **Pros**: No extra collection.
- **Cons**: The benchmark shifts every run; results aren't comparable across
  time. **Rejected** — a moving benchmark can't prove improvement.

### Alternative 2: LLM-as-judge scorer from day one
- **Pros**: Far better correlation with real quality.
- **Cons**: Cost, latency, another model dependency, non-determinism in tests.
- **Why not now**: Start with a deterministic, free, testable proxy; the
  interface is a single function, so upgrading is cheap.

## Implementation Notes

- `app/services/forging.py`: `score_response`, `select_labeled_traces`,
  `freeze_golden_set`, `get_golden_set`, `run_harness`.
- `app/routers/forging.py`: `POST/GET /api/forging/golden-set`,
  `POST /api/forging/harness` — edition-gated, per-user Mongo via `get_mongo_db`.
- Tests in `tests/test_forging.py` cover the pure functions and the Mongo paths
  against an in-memory fake collection.

## References

- [ADR-0001](0001-self-forging-training.md) — Self-Forging Training (parent)
- Guide: [`docs/guides/SELF_FORGING.md`](../guides/SELF_FORGING.md)
