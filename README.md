# AladdinAI

**AladdinAI** is an open-source, self-hosted AI workspace — agents, memory, CRM, and multi-channel messaging under one roof, running entirely in your own infrastructure.

We believe the next wave of AI adoption won't happen in shared clouds. It will happen in companies that need control over their data, their models, and their customer relationships. AladdinAI is the platform that makes that possible without building everything from scratch.

> **Traction:** 436 unique cloners in the first 14 days after public release — organic, zero paid promotion.

> **Status:** actively developed. Most features below are wired end-to-end and usable locally; some surfaces (webhook triggers, BentoML deploy targets, design polish) are still evolving. See `docs/ARCHITECTURE.md` for the full picture.

---

## What's inside

- **Agents** — per-user agents with their own model, system prompt, tool set, and safety stack (ingress/egress moderation via NemoGuard / Llama-Guard, PII redaction via GLiNER).
- **Memory** — private + shared stores with vector search (MongoDB Atlas + NIM embeddings). Memory is extracted automatically per message. Every recall and write decision is logged via pluggable Gates.
- **CRM** — contacts, deals, activities. Every inbound message is auto-attributed to a contact and logged to the activity timeline.
- **Channels** — Telegram, WhatsApp (Cloud API), SMS providers, IMAP/SMTP email. Outgoing webhooks for fan-out.
- **Triggers & routing** — cron-scheduled fan-out tasks via APScheduler, per-agent model overrides, fallback chains across providers.
- **Infrastructure** — manage LLM provider connections, MongoDB clusters, cloud VMs (SSH), and BentoML deployments from the UI.

---

## Built on industry-leading open infrastructure

AladdinAI is architected around three core technologies — chosen for performance, privacy, and real production deployability.

### NVIDIA NIM
We use NIM for LLM inference and embeddings (`llama-3.2-nv-embedqa-1b-v2`). NIM gives us optimized, containerized model serving that runs on-prem or in any cloud — no dependency on shared inference APIs. Every agent in AladdinAI can route to a NIM endpoint, making the entire inference layer sovereign by default.

### MongoDB Atlas
Long-term agentic memory lives in MongoDB Atlas with Atlas Vector Search. We chose Atlas because it handles both the structured data (CRM records, activity timelines) and the vector layer (semantic memory recall) in a single platform — no separate vector DB to manage or sync. This simplifies the architecture and keeps the data model consistent across the product.

### BentoML
BentoML is our framework for deploying and scaling custom tools and local LLMs within the user's own infrastructure. Through the AladdinAI UI, users can manage BentoML deployments directly — making it possible to swap, scale, or version models without touching the codebase.

---

## Quick start

```bash
# 1. Clone & enter the repo
git clone https://github.com/<you>/AladdinAI.git
cd AladdinAI

# 2. Copy env template
cp .env.example .env
# Edit .env — at minimum, set JWT_SECRET before going anywhere near production.

# 3. Install backend (creates .venv) and frontend deps
make install
cd frontend && npm install && cd ..

# 4. Apply database migrations
make migrate

# 5. Run both services (in two terminals)
make dev-backend    # FastAPI on http://localhost:8000
make dev-frontend   # Next.js on http://localhost:3000
```

Open `http://localhost:3000`, register a user, and you'll land on the dashboard. Add at least one **LLM Provider** (Settings → LLM Providers) before creating agents — NVIDIA NIM works out of the box with a free API key.

By default the backend uses SQLite (`backend/aladdinai.db`). To switch to Postgres, uncomment `DATABASE_URL` in `.env` and run `docker compose up postgres -d`.

---

## Tech stack

| Layer       | Tools                                                        |
|-------------|--------------------------------------------------------------|
| Frontend    | Next.js 15, React 19, TailwindCSS, shadcn/ui, sonner         |
| Backend     | FastAPI, SQLAlchemy 2 (async), Alembic, APScheduler          |
| Storage     | SQLite or Postgres (relational), MongoDB Atlas (vectors)     |
| LLM access  | Provider-agnostic (NIM, OpenAI, Anthropic, local via BentoML)|
| Auth        | JWT (HS256) with access + refresh tokens                     |
| Realtime    | Server-sent events for chat streaming                        |

---

## Roadmap

The current release covers the core platform. Here's what's coming next:

- **Marketplace** — shareable agent templates, tool packs, and gate configurations. Users publish; community forks and extends.
- **Multi-tenant SaaS mode** — deploy AladdinAI as a hosted service for your own customers, with per-tenant isolation and billing hooks.
- **Advanced observability** — full trace view per agent turn: memory reads, gate decisions, tool calls, model latency.
- **Expanded channel support** — voice (WebRTC + NIM ASR/TTS), native mobile push, browser extension.
- **One-click cloud deploy** — pre-configured Terraform modules for AWS, GCP, and Azure. Full stack up in under 10 minutes.

---

## Repository layout

```
AladdinAI/
├── backend/         FastAPI service, models, services, tools, migrations
├── frontend/        Next.js 15 dashboard
├── scripts/         dev / install / migration helpers
├── docs/            Architecture & design notes
├── docker-compose.yml
├── Makefile
└── .env.example
```

Each subtree has its own README:
- [`backend/README.md`](backend/README.md) — request lifecycle, services, how to add a tool/gate/channel
- [`frontend/README.md`](frontend/README.md) — page structure, panel pattern, API client
- [`scripts/README.md`](scripts/README.md) — what each shell script does
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — concept doc tying everything together

---

## Common tasks

```bash
make help                          # list all Make targets
make dev-backend                   # FastAPI on :8000 with auto-reload
make dev-frontend                  # Next.js on :3000
make up                            # full stack via docker compose
make down                          # stop docker compose stack
make migration m="add foo table"   # autogenerate alembic revision
make migrate                       # apply pending migrations
make downgrade                     # roll back one alembic step
make clean                         # remove .venv, caches, build artefacts
```

---

## Production notes

- **JWT_SECRET** — replace with `openssl rand -hex 32` before deploying. Anyone who knows it can mint tokens for any user.
- **Database** — switch `DATABASE_URL` to Postgres. SQLite is fine locally but not for multi-worker deployments.
- **Frontend URL** — set `NEXT_PUBLIC_API_URL` to the public backend URL the browser will reach.
- **API keys** — provider keys live in the database (encrypted at rest, set via the UI), not in `.env`.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).