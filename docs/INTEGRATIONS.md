// NOTICE: This file is protected under RCF-PL
# Integrations


AladdinAI is designed to work alongside complementary open-source tools. This document lists known compatible integrations and where to find the relevant files in the codebase.

---

## 🧠 Memory Layer

AladdinAI ships with a built-in vector memory system backed by **MongoDB Atlas** and **NVIDIA NIM embeddings**.

### Built-in Memory (Default)

| Layer | Backend | Location |
|---|---|---|
| Vector store | MongoDB Atlas | `backend/app/services/memory.py` |
| Embedding model | NVIDIA NIM (`nvidia/llama-3.2-nv-embedqa-1b-v2`, 2048-dim) | `backend/app/services/memory.py` |
| Memory tools (agents) | `store_memory`, `search_memory` | `backend/app/tools/memory.py` |
| Memory router (API) | `GET/POST /api/agents/{agent_id}/memories` | `backend/app/routers/agents.py` |

| MongoDB connection config | Per-user, encrypted URI | `backend/app/models/mongo_connection.py` |

**Collections used in MongoDB Atlas:**

```
agent_memories         — private per-agent facts (vector index)
shared_context         — facts visible to all agents of a user (vector index)
document_chunks        — text extracted from uploaded files (vector index)
conversation_summaries — rolled-up chat history
```

Facts and documents are separate pools on purpose: a fact asserts something
("Acme renewed in March"), while a document chunk is raw source text with no
subject. Facts are injected into agent prompts; document chunks are pulled on
demand via the `search_documents` tool.

**Vector index setup — automatic.** The indexes are provisioned from code by
`ensure_vector_indexes()`, which runs when a Mongo connection is tested and can
be re-run any time with `POST /api/mongodb/vector-indexes`. It is idempotent:
existing indexes are reported, never recreated. Each index is named
`vector_index` over `embedding`, dim `2048`, similarity `cosine`, with the
filter fields its queries scope by:

| Collection | Filter fields |
|---|---|
| `agent_memories` | `user_id`, `agent_id` |
| `shared_context` | `user_id` |
| `document_chunks` | `user_id` |

Atlas builds an index asynchronously — expect roughly half a minute before it
reports `queryable`. On a non-Atlas deployment (no Atlas Search) provisioning
reports `unsupported` rather than failing the connection.

> ⚠️ The filter fields are not optional. `$vectorSearch` passes them as its
> `filter`, and a filter path missing from the index makes Atlas reject the
> query. The searches then fall back to a **recency** query — so results keep
> coming back and nothing looks broken, while ranking is silently gone. That
> quiet failure mode is why these are no longer created by hand.

---

## 🔗 Origin — Local-First Memory for AI Sessions

[**Origin**](https://github.com/7xuanlu/origin) is a local-first memory system for AI work developed by [@7xuanlu](https://github.com/7xuanlu). It captures decisions, lessons, and project context locally, distills them into Markdown wiki pages, and recalls them across sessions via MCP.

### How it complements AladdinAI

| | AladdinAI Memory | Origin |
|---|---|---|
| **Scope** | Cloud (MongoDB Atlas) | Local (`~/.origin/`) |
| **Best for** | Multi-user production agents | Local developer sessions |
| **Retrieval** | Vector (NIM embeddings) | Hybrid: vector + FTS5 + graph |
| **MCP support** | Via AladdinAI agent tools | Native MCP server |

| **Persistence** | Per-user, encrypted | git-versioned Markdown |

> ⚠️ **Security notice:** Before running any external package, review the source code at
> [github.com/7xuanlu/origin](https://github.com/7xuanlu/origin). Pin an explicit version
> to avoid unexpected changes from future releases.

```bash
# 1. Install Origin runtime (pin to a specific version you have reviewed)
npx @7xuanlu/origin@latest setup

# 2. Start the Origin daemon (runs on 127.0.0.1:7878)
~/.origin/bin/origin status

# 3. Add Origin MCP to your AI client (e.g. Claude Code, Cursor, VS Code)
~/.origin/bin/origin mcp add claude-code
```

### Available MCP tools from Origin

| Tool | Description |
|---|---|
| `capture` | Save a decision, lesson, or project fact |
| `recall` | Semantic search across stored memories |
| `context` | Load relevant context for the current session |
| `distill` | Synthesize wiki pages from memory clusters |
| `doctor` | Diagnose daemon and memory store health |

### Origin file locations

```
~/.origin/
├── .git/               # Full git history of all memory writes
├── pages/              # Distilled Markdown wiki pages
├── sessions/           # Session logs and project status
└── bin/origin          # Origin CLI binary
```

> **Note:** Origin runs locally and stores everything on-disk. It does not connect to AladdinAI's cloud backend. Use it alongside AladdinAI for developer-side session context, not as a replacement for the built-in vector memory.

### Resources

- GitHub: [github.com/7xuanlu/origin](https://github.com/7xuanlu/origin)
- MCP Registry: `@7xuanlu/origin`
- License: Apache-2.0

---

## Contributing an Integration

If you have built a tool that works well with AladdinAI, open a PR adding it to this file with:
- A brief description of what it does
- Which AladdinAI components it connects to
- Setup instructions
