// NOTICE: This file is protected under RCF-PL
# Architecture Deep-Dive: Building a Multi-Agent AI Workspace with Persistent Memory

*How I built a self-hosted alternative to ChatGPT Teams + Cursor in 3 months, and the architectural decisions that made it possible.*

---

## The Problem

After helping multiple companies evaluate AI tools, I noticed a pattern: teams **want** AI agents, but their compliance team blocks SaaS solutions. The available alternatives were either:

- **Cloud-only tools** (Cursor, ChatGPT Enterprise) — data leaves your VPC
- **Basic chat wrappers** (Open WebUI, AnythingLLM) — no agents, no memory, no workflow
- **Enterprise solutions** ($50k+/year) — Glean, Hebbia, custom enterprise platforms

There was a gap: a **production-ready, self-hosted, multi-agent AI workspace** that didn't require a quarter-million-dollar contract.

So I built [AladdinAI](https://github.com/aliyevaladddin/AladdinAI).

In this post, I'll walk through the architectural decisions I made — what worked, what didn't, and what I'm still uncertain about.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│  Frontend (Next.js 15 + React 19)               │
│  - Agent UI, CRM, settings                      │
│  - SSE for streaming responses                  │
└──────────────┬──────────────────────────────────┘
               │ REST + SSE
┌──────────────▼──────────────────────────────────┐
│  Backend (FastAPI + SQLAlchemy 2 async)         │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │  Agent Runner (orchestrator)            │   │
│  │  ├─ LLM Service (provider-agnostic)     │   │
│  │  ├─ Tools Registry (@tool decorator)    │   │
│  │  ├─ Memory Service (Mongo + vectors)    │   │
│  │  ├─ Safety Stack (NemoGuard, GLiNER)    │   │
│  │  └─ Gates (pre/post execution)          │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │  Channels                               │   │
│  │  Telegram | WhatsApp | Email | SMS      │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │  Terminal Providers (Docker + Traefik)  │   │
│  │  ttyd (local) | wetty (SSH)             │   │
│  └─────────────────────────────────────────┘   │
└──────────────┬──────────────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
┌──────▼──────┐  ┌──────▼─────────────┐
│  Postgres   │  │  MongoDB Atlas     │
│  (state)    │  │  (vectors+memory)  │
└─────────────┘  └────────────────────┘
```


The key design principle: **separation between canonical state (Postgres) and semantic recall (MongoDB)**.

---

## Memory Architecture

The memory layer is the part I'm most proud of — and most uncertain about.

### Three-Tier Memory Model

Every user has three types of memory storage:

```python
# From services/memory.py

PRIVATE_COLLECTION = "agent_memories"
SHARED_COLLECTION = "shared_context"
SUMMARY_COLLECTION = "conversation_summaries"

EMBED_MODEL = "nvidia/llama-3.2-nv-embedqa-1b-v2"
EMBED_DIM = 2048
```

1. **Private memory** (per-agent): Facts only this specific agent should know
2. **Shared context** (per-user): Facts all agents under this user can access
3. **Conversation summaries**: Rolled-up chat history (no vectors yet)

### Why This Layout?

The split solves a real problem: if Agent A learns "the user is allergic to peanuts" during a personal conversation, should Agent B (the work assistant) know that?

The answer depends on **scope**. Some facts are universal (`user.name = "Alex"`), some are agent-specific (`prefers formal tone in this conversation`).

By making the agent explicitly decide via tool calls, we get:
- Clear data ownership
- Easy GDPR compliance (delete by agent_id or user_id)
- No information leaks between agent personas

### Vector Search Setup

I went with **MongoDB Atlas Vector Search** instead of Pinecone/Weaviate. The reasoning:

✅ **One database**: structured CRM data + vector embeddings live together  
✅ **No sync layer**: avoiding the "two sources of truth" problem  
✅ **Atlas Vector Search is good enough**: cosine similarity, filtering, sub-100ms recall  
❌ **Vendor lock-in**: real concern, considering pgvector as self-hosted alternative

### Memory Extraction Pipeline

After each user message, I run an extraction pipeline:

```python
# From services/extraction.py

"""Per-message memory extraction.

After an agent finishes a turn, optionally distill the exchange into a small
set of facts and persist them via the same gates/safety pipeline that backs
the explicit `remember` tool.

Config lives in `agent.tools_config.extraction`:

    {
      "extraction": {
        "enabled": true,
        "model": "<nim model id>" | null,
        "max_facts": 5
      }
    }
"""
```

The flow:
1. User sends message → Agent responds
2. Extraction LLM call analyzes the exchange
3. Returns 0-5 facts as structured JSON
4. Each fact goes through safety stack (PII redaction, content moderation)
5. Approved facts get embedded and stored

**Trade-off I'm wrestling with:** This runs **per message**, which is expensive at scale. Considering:
- Batch extraction every N messages
- Smaller local model for extraction (Llama 3 8B instead of full)
- Skip extraction for trivial messages

If you've solved this differently, I'd love to hear how.

---

## Plugin System

I went all-in on decorators. Three plugin types:

### 1. Tools (`@tool` decorator)

```python
# From tools/base.py


@dataclass

class ToolContext:
    db: AsyncSession
    user_id: int
    agent_id: int | None = None
    session_id: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)



@dataclass

class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    func: ToolFunc

    def openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
```

Adding a new tool:

```python

@tool(
    name="search_contacts",
    description="Search CRM contacts by name or email",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string"}
        },
        "required": ["query"]
    }
)
async def search_contacts(ctx: ToolContext, query: str) -> list[dict]:
    # ctx.user_id is automatically scoped
    # ctx.db is ready to use
    ...
```

The decorator handles:
- Auto-discovery on import
- JSON Schema generation for OpenAI function calling
- User-scoped database queries (no cross-tenant leaks)

### 2. Terminal Adapters (`@terminal_adapter` decorator)

For browser-based terminals (ttyd, wetty):

```python

@terminal_adapter("ttyd")

class TtydAdapter(TerminalAdapter):
    def build_container_spec(self, *, provider_id, user_id, image, manifest, config):
        # Returns Docker container spec
        ...
    
    def build_session_url(self, *, provider_id, url_template, scheme, host, token):
        # Returns user-facing iframe URL
        ...
```

Same pattern as tools — one decorator, auto-registered, type-safe.

### 3. Gates (pre/post execution)

Gates intercept agent execution at key points:

```python

@gate("memory.read.before")
async def log_memory_reads(ctx: GateContext, query: str) -> GateDecision:
    # Decide whether to allow this memory read
    # Log the decision
    return GateDecision.ALLOW
```

This is how the safety stack hooks into agent execution without modifying the runner.

---

## Safety Stack

Three layers of defense:

```python
# Ingress (user → agent)
- NemoGuard: prompt injection detection
- GLiNER: PII detection and redaction
- Llama-Guard: harmful content filtering

# Egress (agent → user)
- Same stack, applied to agent responses
- Custom rules per agent (configurable)

# Tool execution
- Gates evaluate every tool call
- Audit log to gate_log.py
```

The clever bit: **PII redaction phases**. Different operations have different PII tolerance:

```python
# Config-driven phases
safety_pii(phase="ingress")      # Detect & flag, don't block
safety_pii(phase="egress")       # Block if detected
safety_pii(phase="memory_write") # Redact before storing
safety_pii(phase="memory_read")  # Pass through (already filtered)
```

This avoids the common mistake of either being too paranoid (blocking everything) or too permissive (leaking secrets).

---

## Terminal Providers

The terminal subsystem went through several iterations. Final architecture:

```
Browser (iframe)
    │
    │ HTTP/WebSocket
    │
Traefik (forward-auth + path routing)
    │
    │ Internal docker network
    │
Container (ttyd OR wetty)
    │
    │ PTY OR SSH
    │
Target shell
```

**Forward-auth pattern**:

1. Backend issues short-lived token (5 min, HMAC-signed)
2. URL includes `?token=xxx`
3. Traefik calls `/api/terminal/auth` with the token
4. Backend validates, returns session cookie
5. Subsequent requests (CSS, JS, WebSocket upgrade) use the cookie

This avoids exposing terminal containers directly while keeping the user experience seamless.

**The Pydantic + decorator + FSM stack might be overkill for 2 providers** — but it makes adding new ones (Apache Guacamole, code-server) a 2-file change.

---

## LLM Abstraction

Provider-agnostic from day one:

```
LLMService
├── NVIDIA NIM (default, free, no rate limits)
├── OpenAI
├── Anthropic
├── Local models (via BentoML)
└── Per-agent fallback chains
```

The killer feature: **fallback chains**. If your primary model is rate-limited, the agent automatically retries with the next in the chain. No errors visible to the user.

NVIDIA NIM is the default because:
- Free with NVIDIA developer account
- No rate limits (vs OpenAI's hard caps)
- Self-hostable via Docker
- Good model selection (Llama, Mistral, embeddings)

---

## Multi-Channel Inbound

Every channel (Telegram, WhatsApp, Email, SMS) goes through the same flow:

```python
# From services/orchestrator.py

async def handle_inbound_message(channel_type, raw_message):
    # 1. Parse channel-specific format
    parsed = parse_message(raw_message)
    
    # 2. Find or create CRM contact
    contact = await find_or_create_contact(parsed.sender)
    
    # 3. Resolve which agent should handle this
    agent_id = await resolve_agent_id(parsed)
    
    # 4. Run agent with full context
    response = await run_agent(agent_id, parsed.text, contact_id=contact.id)
    
    # 5. Send response back through same channel
    await send_response(channel_type, parsed.sender, response)
    
    # 6. Log activity to CRM timeline
    await log_activity(contact.id, parsed, response)
```

Every conversation gets logged to CRM automatically. No manual data entry, no integration glue code.

---

## Things I'd Do Differently

**1. SQLite as default was a mistake.**  
Works locally, breaks at first concurrent write. Should default to Postgres in a Docker compose.

**2. Memory extraction should be opt-in per agent.**  
Right now it's a config flag, but the default is "on". Defaults matter — most users won't read docs.

**3. Should have built CLI first.**  
`npx aladdin-ai` was added late. Should have been the primary install method from day 1. Onboarding friction kills self-hosted adoption.

**4. Tool versioning is missing.**  
If I change a tool's parameter schema, all agents using it break silently. Need versioned tool interfaces.

---

## What's Next

**Coming soon:**
- IDE with Monaco Editor + AI copilot (Cursor alternative, self-hosted)
- Voice commands (NVIDIA NIM ASR/TTS)
- Video generation pipeline
- SSO and enterprise auth
- Marketplace for agent templates

**Long-term:**
- Pluggable inference engines (vLLM, TGI, custom)
- Multi-tenant SaaS mode
- Visual agent builder (no-code)

---

## Try It Yourself

One command, no clone, no Python setup:

```bash
npx aladdin-ai
```

That pulls multi-arch images (amd64 + arm64), generates secrets, and brings up the full stack. Default install takes ~3 minutes on a decent machine.

- **GitHub:** [github.com/aliyevaladddin/AladdinAI](https://github.com/aliyevaladddin/AladdinAI)
- **Demo:** [aliyev.site/AladdinAI](https://aliyev.site/AladdinAI)
- **License:** Apache 2.0

---

## Feedback Welcome

The whole point of going open source is getting feedback from people building similar systems. Three questions I'd love your input on:

1. **Memory extraction:** Per-message vs batch — what's working for you?
2. **Vector DB:** Anyone happy with pgvector at production scale?
3. **Multi-agent orchestration:** How do you handle agent-to-agent communication without coordination chaos?

Drop a comment, open an issue, or just star the repo if you find the architecture interesting.

Either way — happy building. The self-hosted AI future is much closer than people think.

---

*If you found this useful and want to follow the journey, the project lives at [github.com/aliyevaladddin/AladdinAI](https://github.com/aliyevaladddin/AladdinAI). Star it if you want to follow updates.*
