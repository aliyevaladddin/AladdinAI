# ADR-0002: Data Storage Strategy - MongoDB vs Postgres

**Status**: Accepted

**Date**: 2026-06-04

**Deciders**: Aladdin Aliyev

**Tags**: backend, database, architecture, storage

## Context

AladdinAI uses both MongoDB Atlas and Postgres for data storage. We needed clear guidelines on when to use each database to avoid inconsistency and performance issues.

**Initial confusion:**
- Agent traces were initially considered for MongoDB (as "background data")
- Chat messages were unclear - both databases seemed viable
- Media files needed a decision between local storage and GridFS

## Decision

**Postgres for:**
- ✅ **Chat messages** (`agent_messages` table) - Primary conversational data
- ✅ **Agent traces** (`agent_traces` table) - Training data requiring relational queries
- ✅ **CRM data** - Contacts, deals, activities (relational structure)
- ✅ **User accounts and auth** - Critical transactional data
- ✅ **System settings** - Configuration requiring ACID guarantees

**MongoDB for:**
- ✅ **Vector embeddings** (`agent_memory` collection) - Atlas Vector Search
- ✅ **Media files** - GridFS for images, documents (when enabled)
- ✅ **Per-agent private memory** - Flexible schema, high write volume
- ✅ **Audit logs** - Time-series data with flexible schema

**Key Principle:**
> "Переписка ВСЕГДА в Postgres (не Mongo!); `agent_traces`/память — фон."

## Consequences

### Positive
- **Clear separation** - No ambiguity about where data goes
- **Performance optimization** - Right tool for each job
- **Backup strategy** - Can treat databases differently
- **Query efficiency** - Relational queries in Postgres, vector search in Mongo

### Negative
- **Dual maintenance** - Two database systems to monitor
- **Complexity** - Developers must know which DB to use
- **Cross-DB queries** - Can't easily join data across databases

### Neutral
- Both databases required anyway (Vector Search needs MongoDB)
- Most queries are within one database

## Alternatives Considered

### Alternative 1: Postgres Only (with pgvector)
- **Pros**: Single database, simpler ops, better ACID
- **Cons**: pgvector less mature than Atlas Vector Search, no GridFS equivalent
- **Why not chosen**: MongoDB Atlas $500 credits already secured, Vector Search battle-tested

### Alternative 2: MongoDB Only
- **Pros**: Single database, flexible schema
- **Cons**: Weak transactional support, poor for relational CRM data
- **Why not chosen**: CRM and chat need strong consistency

### Alternative 3: Postgres Primary + MongoDB Cache
- **Pros**: Postgres as source of truth
- **Cons**: Synchronization complexity, cache invalidation issues
- **Why not chosen**: Over-engineered for current scale

## Implementation Notes

### Storage Matrix

| Data Type | Database | Collection/Table | Reason |
|-----------|----------|------------------|--------|
| Chat messages | Postgres | `agent_messages` | Primary conversational data, relational |
| Agent traces | Postgres | `agent_traces` | Training queries need SQL |
| Vector memory | MongoDB | `agent_memory` | Atlas Vector Search |
| Media files | MongoDB | GridFS | Large binary storage |
| CRM contacts | Postgres | `crm_contacts` | Relational structure |
| User accounts | Postgres | `users` | ACID required |
| System settings | Postgres | `system_settings` | Configuration integrity |
| Audit logs | MongoDB | `audit_logs` | High write volume, flexible |

### Migration Path
1. ✅ Moved media storage to MongoDB GridFS (2026-06-04)
2. ✅ Clarified chat messages stay in Postgres
3. ✅ Documented in memory: `project_aladdinai_mongodb_media_storage.md`

### Gotchas on Render.com
- Atlas whitelist must include `0.0.0.0/0` for Render IPs
- `ALADDIN_EDITION=internal` required for trace writes
- Connection string format: `mongodb+srv://...` (not `mongodb://`)

## References

- [Memory: MongoDB media storage](../../../claude-memory/project_aladdinai_mongodb_media_storage.md)
- [Memory: Render deploy gotchas](../../../claude-memory/project_aladdinai_render_deploy.md)
- [MongoDB for Startups: $500 credits](../../../claude-memory/project_aladdinai_mongodb_startup.md)
- Related: ADR-0001 (Self-Forging uses Postgres for traces)
