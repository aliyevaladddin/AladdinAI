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
agent_memories         — private per-agent facts (vector index required)
shared_context         — facts visible to all agents of a user (vector index required)
conversation_summaries — rolled-up chat history
```

**Vector index setup (Atlas UI):**
- Collection: `agent_memories` → Index name: `vector_index`, field: `embedding`, dim: `2048`, similarity: `cosine`
- Collection: `shared_context` → same index config, filter on `user_id`

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

### Quick setup (local development)

```bash
# 1. Install Origin runtime
npx -y @7xuanlu/origin setup

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
