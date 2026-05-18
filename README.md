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

One command, no `git clone`, no Python, no Node toolchain — just Docker.

```bash
npx aladdin-ai
```

That pulls prebuilt images from GHCR (multi-arch: amd64 + arm64), generates a `.env` with cryptographically-secure secrets, and brings up the stack:

```
✓ Services running
  Frontend: http://localhost:3000
  Backend:  http://localhost:8000
```

Open `http://localhost:3000`, register a user, and you'll land on the dashboard. Add at least one **LLM Provider** (Settings → LLM Providers) before creating agents — NVIDIA NIM works out of the box with a free API key.

### Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS / Windows) or `docker` + `docker compose` plugin (Linux)
- Node.js 18+ (just to run `npx`)

### Day-to-day commands

```bash
npx aladdin-ai up               # start services
npx aladdin-ai down             # stop services
npx aladdin-ai restart backend  # restart one service
npx aladdin-ai logs -f          # tail logs
npx aladdin-ai update           # pull the latest images and recreate
npx aladdin-ai doctor           # diagnose setup issues
```

See [`cli/README.md`](cli/README.md) for the full command reference.

---

## Development setup (for contributors)

If you want to modify the code rather than just use AladdinAI, install from source — this gives you a writable repo and local Docker builds:

```bash
npx aladdin-ai init --source
# or, manually:
git clone https://github.com/aliyevaladddin/AladdinAI.git
cd AladdinAI
cp .env.example .env       # generate secrets manually before exposing publicly
docker compose up --build  # builds backend/frontend from your local source
```

For a non-Docker workflow with hot-reload (running FastAPI / Next.js directly on the host):

```bash
make install           # creates .venv, installs Python deps
cd frontend && npm install && cd ..
make migrate           # apply Alembic migrations to your local DB
make dev-backend       # FastAPI on :8000 with --reload
make dev-frontend      # Next.js on :3000 with --reload
```

This is the fastest loop when iterating on backend code — no image rebuilds.

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