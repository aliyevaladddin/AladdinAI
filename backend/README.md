// NOTICE: This file is protected under RCF-PL
# Backend

FastAPI service that powers AladdinAI. Async SQLAlchemy on top of SQLite or
Postgres for relational state, MongoDB Atlas for vector memory, JWT auth, and
APScheduler embedded in the FastAPI process for cron-style triggers.

```
backend/
├── app/
│   ├── main.py            FastAPI app, router registration, startup hooks
│   ├── config.py          Pydantic settings (env-driven)
│   ├── database.py        Async engine + session factory
│   ├── security.py        JWT, password hashing, current-user dep
│   ├── models/            SQLAlchemy ORM models
│   ├── schemas/           Pydantic request/response models
│   ├── routers/           HTTP endpoints (one file per resource)
│   ├── services/          Business logic, no FastAPI imports
│   └── tools/             Agent-callable tools (CRM, memory, delegation)
├── alembic/               Migration scripts
└── requirements.txt
```

---

## Layers

The codebase splits into three layers:

1. **Routers** (`app/routers/`) — thin: parse input, check auth, call a
   service, shape the response. No business logic.
2. **Services** (`app/services/`) — all the actual logic. Pure functions or
   small classes that take a DB session and inputs. Easy to test, reusable
   from background tasks.
3. **Tools** (`app/tools/`) — services exposed to LLMs as callable functions.
   Each tool wraps a service call and declares a JSON schema for arguments.

Models (`app/models/`) describe the SQL schema. Schemas (`app/schemas/`) are
the API contract; never expose ORM objects directly.

---

## Request lifecycle: a chat message

When a user sends a chat message, this is the path through the system:

```
POST /api/chat/{agent_id}/messages
        │
        ▼
routers/chat.py            authenticate, load agent
        │
        ▼
services/safety.py         ingress moderation + PII redaction (configurable)
        │
        ▼
services/agent_runner.py   build prompt, inject shared+private memory,
        │                  call LLM via services/llm_service.py
        │
        ├── tool_calls? ─► tools/* (CRM, memory, inter-agent delegation)
        │                  each tool runs through services/gates.py
        │
        ▼
services/safety.py         egress moderation + PII redaction
        │
        ▼
services/extraction.py     pull facts from the exchange, write to memory
        │                  (private to agent + shared if user-level)
        ▼
SSE stream back to client
```

Inbound webhook messages (Telegram, WhatsApp, SMS) follow the same path
starting from `services/orchestrator.py`, which resolves the contact, picks
the responding agent, and feeds the message in as if it came from chat.

---

## Services worth knowing

| Service                        | Role                                                |
|--------------------------------|-----------------------------------------------------|
| `agent_runner.py`              | Drives an agent turn: prompt, LLM call, tool loop   |
| `orchestrator.py`              | Routes inbound channel messages to the right agent  |
| `llm_service.py`               | Provider-agnostic chat/completion + embeddings      |
| `memory.py`                    | List/insert/search facts in MongoDB                 |
| `extraction.py`                | LLM-driven fact extraction after each exchange      |
| `safety.py`                    | NemoGuard / Llama-Guard / GLiNER PII pipelines      |
| `gates.py` + `gate_log.py`     | Pluggable decisions on handoff/memory/recall        |
| `triggers.py`                  | APScheduler integration, cron + presets             |
| `messaging_service.py`         | Telegram / WhatsApp / SMS send paths                |
| `email_service.py`             | IMAP poll + SMTP send                               |
// [RCF:PROTECTED]
| `webhook_service.py`           | Outgoing webhook fan-out with HMAC signing          |
| `crm_service.py`               | Contacts / deals / activities                       |
| `recommended_models.py`        | Hand-picked NIM models surfaced in the UI           |

---

## How to extend

### Add a new agent tool

1. Create `app/tools/<your_tool>.py` exposing a class derived from
   `tools.base.Tool` (declares `name`, `description`, `args_schema`, and an
   async `run()`).
2. Register it in the tool registry where existing tools are wired (search
   for `inter_agent` to find the registration site).
3. Tools that need gating (e.g. memory writes, handoffs) call
   `services.gates.check(...)` before acting.

### Add a new gate

1. Add a function in `services/gates.py` that takes the relevant context and
   returns a decision (allow / deny / mutate).
2. Call it from the service that needs the check.
3. `services/gate_log.py` will record the decision automatically if you go
   through `gates.check`.

### Add a new channel

1. Model: a row in `messaging_channel.py` already covers most providers. Add
   a `type` value if needed.
2. Inbound webhook: extend `routers/webhooks.py` with a `POST
   /webhooks/<provider>/{channel_id}` handler. Normalize the payload to
   `{contact_external_id, text}` and call `orchestrator.handle_inbound(...)`.
3. Outbound: add a send function in `services/messaging_service.py` that the
   orchestrator can dispatch to.

### Add a database table

```bash
# 1. Add or modify a model under app/models/
# 2. Generate migration
make migration m="add foo table"
# 3. Inspect the autogenerated file under backend/alembic/versions/
# 4. Apply
make migrate
```

---

## Background work

Two mechanisms run things outside HTTP request scope:

- **`asyncio.create_task`** for fire-and-forget work tied to a request
  (e.g. agent message processing after webhook ingestion). Each task opens
  its own DB session — never reuse the request's session.
- **APScheduler** (started from `main.py`'s `startup` hook) for cron-style
  triggers. State lives in the `agent_triggers` table; on boot
  `triggers.hydrate_from_db()` re-registers every enabled trigger.

There is no Celery/Redis broker. If you need durable retries across process
restarts, that's the place to add one.

---

## Running locally

```bash
make install                       # creates .venv, installs requirements
make migrate                       # apply pending migrations
make dev-backend                   # uvicorn with --reload on :8000
```

Interactive API docs at <http://localhost:8000/docs>. The OpenAPI schema is
the source of truth for what the frontend expects.

---

## Configuration

All config lives in `app/config.py` and is loaded from environment via
`pydantic-settings`. See [`.env.example`](../.env.example) for the full list
with descriptions. Provider API keys are NOT in env — they're stored in the
// [RCF:PROTECTED]
database (encrypted) and managed through the LLM Providers UI.
