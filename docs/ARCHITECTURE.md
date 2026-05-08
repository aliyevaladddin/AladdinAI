# Architecture

This document explains the *idea* behind AladdinAI — what the parts are,
why they exist, and how they fit together. For the file-by-file map, read
[`backend/README.md`](../backend/README.md) and
[`frontend/README.md`](../frontend/README.md).

---

## The premise

Off-the-shelf chat UIs treat an agent as "a system prompt + a model." That
falls apart the moment you want it to:

- remember things across sessions,
- not leak the things it remembered,
- delegate to other agents,
- pick up messages from Telegram or email,
- run on a schedule,
- be governable (who decided to write that fact? why was that handoff allowed?).

AladdinAI is the smallest set of moving parts that gives you all of the above
in one workspace, self-hosted, with the user (you) in control of every
provider key, every memory write, and every channel binding.

---

## Core concepts

### Agent

An agent is a row in `agents` plus a configuration bundle:

- **Identity**: name, description, system prompt.
- **Brain**: which provider/model to use; routing fallbacks.
- **Tools**: which capabilities it can invoke (CRM access, memory write,
  delegation to specific other agents, etc.).
- **Safety profile**: which moderation/PII checks run on which phases.
- **Gates**: rules that decide whether tool calls go through (handoff,
  memory write, recall rerank).
- **Extraction policy**: what to mine from each conversation for memory.

Agents are per-user. Multiple users on the same instance get isolated
agents and isolated memory.

### Memory

Memory is **MongoDB-backed** (not Postgres). Each fact is a document with
an embedding (NIM-generated, 2048-dim) so we can vector-search it later.

Two scopes:

- **Private** — visible only to the agent that wrote it. Agent-specific
  knowledge: "the user prefers terse answers when they ask about deploys."
- **Shared** — visible to every agent of that user. User-level knowledge:
  "the user's daughter is named Anna."

A turn injects both scopes into context: relevant private facts (top-k
vector search) and relevant shared facts. After the turn, an extraction
LLM call produces new facts and writes them — private by default, shared
when the fact is about the user as a person rather than the agent
relationship.

This split is why we run extraction *per message* (each user/assistant
exchange) rather than per session: it gives the extractor enough recent
context without letting old turns drown out new ones, and it lets shared
facts surface to other agents within minutes instead of session boundaries.

### Gates

A **gate** is a checkpoint with a yes/no/mutate decision and a reason.
Three live today:

- `handoff` — should agent A be allowed to delegate to agent B for this
  prompt?
- `memory_write` — is this fact worth saving? Is it sensitive?
- `recall_rerank` — among the top-k vector hits, which actually belong in
  the prompt?

Each call goes through `services/gate_log.py` and lands in `gate_decisions`
so you can audit later: "why did agent X share that with agent Y?"

### Safety

Two things, run as separate phases:

- **Moderation** — NemoGuard or Llama-Guard checks for jailbreaks /
  policy violations. Configurable on `ingress` (user → agent) and `egress`
  (agent → user).
- **PII redaction** — GLiNER pulls names, emails, phone numbers, etc.
  Phases: `ingress`, `egress`, `memory_write`, `memory_read`. Off by
  default for the memory phases because over-redacting kills recall (this
  was a real bug — see git history).

Each agent picks which phases run. There's no global "safety on/off"
because the tradeoff is different for an internal CRM agent than a
customer-facing support agent.

### Tools

Tools are functions the LLM can call. They're declared with a JSON schema
and registered per agent. Built-ins:

- `crm.*` — read/write contacts, deals, log activities.
- `memory.write` — explicit "remember this" call (in addition to
  background extraction).
- `inter_agent.delegate` — hand the task to another agent. Goes through
  the `handoff` gate.

Adding a tool means adding a class under `backend/app/tools/` and
registering it. Anything stateful goes through a service so the same
logic is reachable from background tasks too.

### Channels

A **channel** is a pipe that brings external messages in or sends agent
replies out. Telegram, WhatsApp Cloud API, SMS providers, IMAP/SMTP for
email. They share a normalization step — by the time `orchestrator.py`
sees the inbound, it looks like `{contact, text, channel}` regardless of
where it came from.

The orchestrator:

1. Resolves or creates a contact from the channel-specific external ID.
2. Logs an `activity` row of type `message_in`.
3. Picks the responding agent (per-channel routing or a default).
4. Feeds the message into the same path a chat UI message would take.

Outbound is simpler — `messaging_service.py` knows how to talk to each
provider and is called from the agent's reply step.

### Triggers

A **trigger** is a cron expression + a list of agents + a task template.
On fire, it inserts an `agent_message` row for each agent and processes
them in the background. Powered by APScheduler running inside the FastAPI
process; state is hydrated from the `agent_triggers` table on boot, so
restarts don't lose schedules.

Two flavors:

- **Preset** — friendly names (`every_morning_9`, `weekdays_9`, …) that
  map to canonical cron expressions. UI offers these by default.
- **Cron** — raw 5-field cron for power users; the UI has a "preview next
  fire" button backed by `croniter`.

We didn't add Celery + Redis because the workload (a few cron jobs per
user) doesn't justify the operational cost. If durable retries across
process crashes become important, this is the layer that grows.

### Routing

Each agent picks a default model. The router config lets you set
fallbacks: if the primary provider fails or returns garbage, try the next
one. There's also a global default (`/dashboard/router`) for new agents.
Provider keys live in the database, encrypted at rest, set via the
LLM Providers UI — never in `.env`.

---

## Data model in one breath

```
users ──┬── agents ──┬── agent_messages         (per-turn ledger)
        │            ├── tool calls (logged via gates)
        │            └── extraction → mongo memory
        ├── contacts ── activities (message_in/out, notes, deal events)
        ├── deals
        ├── messaging_channels (telegram/whatsapp/sms)
        ├── email_accounts (imap+smtp)
        ├── outgoing_webhooks
        ├── agent_triggers (cron schedules)
        ├── llm_providers (encrypted keys)
        ├── mongo_connections
        ├── vms (ssh credentials)
        ├── bentoml_connections
        └── router_config
```

Relational state lives in SQLite or Postgres. Vector memory lives in
MongoDB Atlas. Gate decisions and activities are append-only.

---

## A full inbound message lifecycle

User sends a message to your Telegram bot:

1. Telegram → `POST /api/webhooks/telegram/{channel_id}` (signed request).
2. `routers/webhooks.py` normalizes payload, calls
   `orchestrator.handle_inbound(...)`.
3. Orchestrator resolves contact (creating one if first contact), writes
   `activity{type=message_in}`, picks responding agent.
4. `safety.ingress` runs (moderation + PII per agent config).
5. `agent_runner` builds the prompt: system prompt + recent turns +
   relevant memory (private vector search + shared vector search, both
   filtered by the `recall_rerank` gate).
6. LLM call. If the response contains tool calls:
   - `inter_agent.delegate` → `handoff` gate → recursive run.
   - `crm.*` → service call, logged as activity.
   - `memory.write` → `memory_write` gate → mongo insert.
7. Final assistant text → `safety.egress`.
8. Reply sent back via `messaging_service.send_telegram(...)`.
9. `extraction` runs on the (user, assistant) pair, produces fact
   candidates, each goes through the `memory_write` gate, surviving ones
   land in mongo.

Every gate decision and every activity is recorded. Re-running the same
input later should give you a near-identical trace.

---

## Why these choices

- **FastAPI + async SQLAlchemy** because most of the work is I/O-bound
  (LLM calls, vector search, webhook deliveries). Async keeps a single
  worker handling many in-flight conversations.
- **MongoDB for memory, SQL for everything else.** Vector search there is
  first-class and managed; we don't want to run a Postgres + pgvector
  stack alongside a relational one.
- **APScheduler in-process** beats Celery for our scale. State is in the
  DB, hydration on boot is cheap, restarts don't lose schedules.
- **JWT with refresh tokens** because the frontend is a SPA and the
  backend has no session store. Short-lived access, longer-lived refresh.
- **Provider-agnostic LLM service** so the platform doesn't bet on one
  vendor. NIM is the current default because it's free at the rate we
  need; OpenAI / Anthropic / local-via-BentoML drop in by adding rows in
  `llm_providers`.
- **Self-hosted, single binary-ish** — one Postgres, one Mongo cluster,
  two processes (FastAPI + Next.js). No message broker, no separate
  worker fleet, no managed queue. You can run the whole thing on one box.

---

## What's not here

Things people sometimes expect that we explicitly don't have:

- **No multi-tenant SaaS layer.** Users exist; "organizations" don't.
  Add a tenancy column if you need it.
- **No agent marketplace.** Agents are configured per-user in the UI.
- **No vector store inside Postgres.** Memory is Mongo. If you want one
  database, port the memory service.
- **No durable job queue.** Triggers are best-effort within a running
  process. If a fire happens during a restart, it's missed (next fire is
  scheduled normally).
- **No fine-tuning pipeline.** Bring your own fine-tuned model and
  register it as a provider/model.

---

## Pointers

- Backend internals: [`backend/README.md`](../backend/README.md)
- Frontend internals: [`frontend/README.md`](../frontend/README.md)
- Scripts: [`scripts/README.md`](../scripts/README.md)
- Env vars: [`.env.example`](../.env.example)
