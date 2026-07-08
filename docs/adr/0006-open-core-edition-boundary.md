// NOTICE: This file is protected under RCF-PL
# ADR-0006: Open-Core Edition Boundary via ALADDIN_EDITION

**Status**: Accepted

**Date**: 2026-06-06

**Deciders**: Aladdin Aliyev

**Tags**: backend, product, open-core, self-forging, licensing

## Context

AladdinAI is open-source and self-hosted, but it also has a commercial path:
the **Self-Forging** loop captures agent traces (`tracing.py` → `agent_traces`)
that are later used to fine-tune a proprietary forged model served from a
commercial endpoint. We need a clean, single line between:

- what a community self-hoster runs (no commercial instrumentation), and
- what our own infrastructure runs (trace-capture ON to feed Self-Forging).

The line must be explicit, auditable, and not leak commercial behavior into the
public image by accident.

## Decision

Gate edition-specific behavior behind a single config field:

```python
edition: str = Field(default="community", validation_alias="ALADDIN_EDITION")
```

- `community` (default, public self-hosted image): Self-Forging trace-capture is
  **OFF**. A community user carries no commercial instrumentation.
- `internal` / `cloud` (our own infra): trace-capture **ON** by default.

Two override layers sit on top, so the edition is a default, not a hard wire:

1. per-agent `tracing.enabled` flag — always overrides the edition default;
2. `TRACING_DISABLED` env var — global kill-switch above both.

The data forged is **our own** traces + synthetic data, never customer data.

## Consequences

### Positive
- One field defines the open-core boundary — easy to reason about and audit.
- The public image ships clean (capture OFF) by default — privacy-respecting.
- Commercial instrumentation is opt-in by deployment, not by code fork.
- Per-agent + global overrides keep it flexible without blurring the default.

### Negative
- A misconfigured `ALADDIN_EDITION=internal` on a public deploy would enable
  capture unexpectedly — operators must understand the flag (documented in config).

### Neutral
- Same codebase serves both editions; the difference is configuration, not a fork.
- Conversation history always persists to Postgres regardless of edition; only the
  background trace/memory capture is edition-gated.

## Alternatives Considered

### Alternative 1: Separate community vs commercial repositories/forks
- **Description**: Maintain two codebases.
- **Pros**: Hard isolation of commercial code.
- **Cons**: Double maintenance, drift, painful backports.
- **Why not chosen**: Open-core via config keeps a single source of truth.

### Alternative 2: Build-time feature flags / compilation
- **Description**: Strip commercial code from the community build.
- **Pros**: Commercial code physically absent from public artifacts.
- **Cons**: Complex build matrix; Python has no clean dead-code stripping.
- **Why not chosen**: A runtime default + overrides is simpler and sufficient.

### Alternative 3: Always-on capture with a consent prompt
- **Description**: Capture everywhere, ask users to opt out.
- **Pros**: Maximal data.
- **Cons**: Hostile default; violates the sovereign / self-hosted promise.
- **Why not chosen**: Community default must be OFF.

## Implementation Notes

- Field: `backend/app/config.py` (`edition`, alias `ALADDIN_EDITION`).
- Capture wiring: `services/tracing.py` → `agent_traces`.
- Note: a Mongo-backed background write path requires `internal`/`cloud` to be
  active; on `community` those background writes are intentionally skipped.

## References

- [ADR-0001: Self-Forging Training](0001-self-forging-training.md)
- `backend/app/config.py`, `backend/app/services/tracing.py`
