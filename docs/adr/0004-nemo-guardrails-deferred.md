// NOTICE: This file is protected under RCF-PL
# ADR-0004: NeMo Guardrails Deferred Due to langchain-core Conflict

**Status**: Accepted

**Date**: 2026-06-27

**Deciders**: Aladdin Aliyev

**Tags**: backend, safety, dependencies, guardrails

## Context

The safety stack (`services/safety.py`) screens agent traffic for jailbreaks and
policy violations using NemoGuard / Llama-Guard model endpoints. We evaluated
adding **NVIDIA NeMo Guardrails** (`nemoguardrails`) as a programmable rails layer
on top of model-based moderation: declarative `config.yml` + Colang flows per
safety preset, loaded via `LLMRails` inside `safety._moderate`.

A prototype was built (`safety_policies/<preset>/` with `config.yml` + `discussions.co`).
It worked in isolation but broke the agent runtime.

## Decision

**Defer NeMo Guardrails. Do not ship it.** The prototype was fully removed:
`safety.py` reverted to its prior state, `safety_policies/` deleted, and
`nemoguardrails` left out of `requirements.txt`.

Root cause is an **irreconcilable dependency conflict**:

- `nemoguardrails 0.10.0` requires `langchain-core <0.3.0`
- Tool-calling agents (`langchain-openai`, `langgraph`) and `skillspector` require `langchain-core >=1.x`

These cannot coexist in one environment. Installing `nemoguardrails` downgrades
`langchain-core` to 0.2.x, which **breaks agent tool-calling** (the `tracing_enabled`
and `pydantic_v1` APIs change between majors). Guardrails are a safety nice-to-have;
tool-calling is core product. Core wins.

## Consequences

### Positive
- Agent tool-calling stays on `langchain-core >=1.x` — no regression.
- Dependency tree stays resolvable; CI installs cleanly.
- Safety is unaffected: model-based moderation (NemoGuard / Llama-Guard endpoints)
  remains the active path.

### Negative
- No declarative Colang rails layer. Programmable conversation-flow guardrails
  are unavailable until the conflict is resolved upstream.

### Neutral
- Any dormant `nemo_guardrails.enabled` config branch must fail safe: without the
  package installed it falls through to the standard LLM classifier, never crashes.

## Alternatives Considered

### Alternative 1: Pin langchain-core <0.3 to satisfy nemoguardrails
- **Description**: Downgrade the whole tree to NeMo's required range.
- **Pros**: NeMo Guardrails would work.
- **Cons**: Breaks tool-calling agents and skillspector — the product core.
- **Why not chosen**: Sacrifices core functionality for an optional layer.

### Alternative 2: Isolate NeMo in a separate process/service
- **Description**: Run guardrails behind its own venv/microservice, call over HTTP.
- **Pros**: No dependency clash; both halves keep their own langchain-core.
- **Cons**: Operational overhead, extra deploy unit, added latency per turn.
- **Why not chosen**: Not worth it yet; revisit if rails become a hard requirement.

### Alternative 3: Wait for a nemoguardrails release supporting langchain-core 1.x
- **Description**: Defer until upstream catches up.
- **Pros**: Zero added complexity; clean integration later.
- **Cons**: No timeline; blocked on a third party.
- **Why not chosen** (as a blocker): chosen as the *path forward*, not a blocker —
  ship without it now, integrate when compatible.

## Implementation Notes

- Re-enable requires **either** a `nemoguardrails` build compatible with
  `langchain-core >=1.x`, **or** extracting guardrails (and skillspector audit)
  into a separate process with its own dependency set.
- Until then, treat any guardrails branch as dead-code/fallback that degrades
  gracefully to model-based moderation.

## References

- [ADR-0001: Self-Forging Training](0001-self-forging-training.md)
- `backend/app/services/safety.py`
