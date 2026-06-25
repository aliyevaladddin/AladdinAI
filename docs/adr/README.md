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

### Security
- [ADR-0003](0003-rcf-webhook-auth.md) - RCF Protocol

### Frontend
- (Coming soon)

### DevOps
- (Coming soon)

---

**Template**: [template.md](template.md)
