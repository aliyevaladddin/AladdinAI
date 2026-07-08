// NOTICE: This file is protected under RCF-PL
# ADR-0001: Self-Forging Model Training from Agent Traces

**Status**: Accepted

**Date**: 2026-06-06

**Deciders**: Aladdin Aliyev

**Tags**: backend, ml, self-forging, architecture

## Context

AladdinAI generates thousands of agent execution traces daily. These traces contain:
- User requests and agent responses
- Tool calls and their results
- Multi-turn conversations
- Success/failure patterns

We needed a way to continuously improve model performance without relying on external LLM providers and their associated costs.

## Decision

Implement a **Self-Forging** system that:
1. Captures all agent traces to `agent_traces` table in Postgres
2. Exports traces in training format (conversations, tool calls, outcomes)
3. Trains a custom model from these traces using open-source base models
4. Hosts the forged model at `api.aliyev.site/v1` endpoint
5. Uses `ALADDIN_EDITION=internal` flag to enable trace capture


**Key Design Choices:**
- Traces stored in Postgres (not MongoDB) for relational queries
- Privacy: Only system traces, never user chat data
- Monetization: Forged endpoint as premium feature
- Open core boundary: Community edition has tracing OFF by default

## Consequences

### Positive
- **Self-improving system** - Gets smarter with usage
- **Cost reduction** - Less dependency on external APIs
- **Data sovereignty** - Training data stays in our control
- **Competitive advantage** - Unique to AladdinAI
- **Monetization path** - Forged endpoint as paid service

### Negative
- **Storage overhead** - Traces consume database space
- **Compute cost** - Model training requires GPU resources
- **Complexity** - Additional ML pipeline to maintain
- **Quality uncertainty** - Forged model may underperform base models initially

### Neutral
- Training happens offline, doesn't impact runtime performance
- Users can opt-out by using community edition

## Alternatives Considered

### Alternative 1: External Fine-tuning Services (OpenAI, Anthropic)
- **Pros**: No infrastructure, proven quality
- **Cons**: Expensive, data leaves our control, vendor lock-in
- **Why not chosen**: Against sovereignty principles, high cost at scale

### Alternative 2: RL from Human Feedback (RLHF)
- **Pros**: Higher quality improvements
- **Cons**: Requires human labeling, slow feedback loop
- **Why not chosen**: Too resource-intensive for early stage

### Alternative 3: No Custom Model (Use Base Models Only)
- **Pros**: Simplest, lowest maintenance
- **Cons**: Misses opportunity for differentiation and cost savings
- **Why not chosen**: Limits competitive advantage

## Implementation Notes

### Phase 1 (Completed - 2026-06-04)
- ✅ `tracing.py` service captures traces to `agent_traces` table
- ✅ `ALADDIN_EDITION` flag controls trace capture
- ✅ Open core boundary established

### Phase 2 (In Progress)
- Export pipeline for training data
- Training scripts using base models (Llama, Mistral)
- Model evaluation metrics

### Phase 3 (Planned)
- Forged endpoint deployment at `api.aliyev.site/v1`
- A/B testing framework (base vs forged)
- Continuous training pipeline

## References

- [Tracing Service](../../backend/app/services/tracing.py)
- Related: ADR-0002 (MongoDB vs Postgres for traces)
