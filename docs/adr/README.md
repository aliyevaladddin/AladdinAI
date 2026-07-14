// NOTICE: This file is protected under RCF-PL
# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for AladdinAI.

## What is an ADR?

An Architecture Decision Record (ADR) captures an important architectural decision made along with its context and consequences. It helps teams understand:
- **Why** a decision was made
- **What** alternatives were considered
- **What** trade-offs were accepted

## Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [0001](0001-self-forging-training.md) | Self-Forging Model Training from Agent Traces | ✅ Accepted | 2026-06-06 |
| [0002](0002-mongodb-vs-postgres.md) | Data Storage Strategy - MongoDB vs Postgres | ✅ Accepted | 2026-06-04 |
| [0003](0003-rcf-webhook-auth.md) | RCF Protocol for Webhook Authentication | ✅ Accepted | 2026-05-30 |
| [0004](0004-nemo-guardrails-deferred.md) | NeMo Guardrails Deferred (langchain-core conflict) | ✅ Accepted | 2026-06-27 |
| [0005](0005-media-storage-abstraction.md) | Unified Media Storage (Local FS vs GridFS) | ✅ Accepted | 2026-06-04 |
| [0006](0006-open-core-edition-boundary.md) | Open-Core Edition Boundary via ALADDIN_EDITION | ✅ Accepted | 2026-06-06 |
| [0007](0007-voice-pipeline-riva.md) | Voice Pipeline on NVIDIA Riva + ffmpeg | ✅ Accepted | 2026-06-27 |
| [0008](0008-orders-status-history-in-activity-metadata.md) | Orders as a Distinct Entity; Status History in Activity Metadata | ✅ Accepted | 2026-07-14 |

## Status Definitions

- **Proposed** - Under discussion, not yet decided
- **Accepted** - Decision made and implemented
- **Deprecated** - No longer relevant or superseded
- **Superseded by ADR-XXXX** - Replaced by a newer decision

## Creating a New ADR

1. Copy the template:
   ```bash
   cd docs/adr
   cp template.md NNNN-short-title.md
   ```

2. Fill in all sections:
   - Context: Why is this decision needed?
   - Decision: What are we doing?
   - Consequences: What are the impacts?
   - Alternatives: What else did we consider?

3. Get review from team/stakeholders

4. Update this index with the new ADR

## Guidelines

- **Be concise** - ADRs should be scannable
- **Be honest** - Document negative consequences too
- **Be specific** - Include concrete examples and code
- **Link references** - Connect to related code, issues, discussions
- **Update status** - Mark as Deprecated/Superseded when needed

## Categories

### Backend & Infrastructure
- [ADR-0001](0001-self-forging-training.md) - Self-Forging Training
- [ADR-0002](0002-mongodb-vs-postgres.md) - Database Strategy
- [ADR-0005](0005-media-storage-abstraction.md) - Media Storage (Local FS vs GridFS)
- [ADR-0006](0006-open-core-edition-boundary.md) - Open-Core Edition Boundary
- [ADR-0008](0008-orders-status-history-in-activity-metadata.md) - Orders Entity & Status History

### Safety & Voice
- [ADR-0004](0004-nemo-guardrails-deferred.md) - NeMo Guardrails Deferred
- [ADR-0007](0007-voice-pipeline-riva.md) - Voice Pipeline on NVIDIA Riva

### Security
- [ADR-0003](0003-rcf-webhook-auth.md) - RCF Protocol

---

**Template**: [template.md](template.md)
