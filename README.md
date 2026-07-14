
[![Site status](https://img.shields.io/website?url=https%3A%2F%2Faliyev.site%2FAladdinAI&style=flat-square&color=4ecdc4&logo=vercel&logoColor=white&label=live+demo)](https://aliyev.site/AladdinAI/)
![Repo size](https://img.shields.io/github/repo-size/aliyevaladddin/AladdinAI?style=flat-square&color=4ecdc4&logo=proton%20drive&logoColor=white)
[![CI](https://img.shields.io/github/actions/workflow/status/aliyevaladddin/AladdinAI/ci.yml?style=flat-square&color=4ecdc4&label=CI&logo=githubactions&logoColor=white)](https://github.com/aliyevaladddin/AladdinAI/actions/workflows/ci.yml)
[![Deploy to Render](https://img.shields.io/badge/deploy%20to-render-4ecdc4?style=flat-square&logo=render&logoColor=white)](https://render.com/deploy?repo=https://github.com/aliyevaladddin/AladdinAI)
![Last commit](https://img.shields.io/github/last-commit/aliyevaladddin/AladdinAI?style=flat-square&color=4ecdc4&logo=githubcopilot&logoColor=white)
![GitHub commit activity](https://img.shields.io/github/commit-activity/m/aliyevaladddin/AladdinAI?style=flat-square&color=4ecdc4&logo=dependabot&logoColor=white)

---
## ◈ GitHub Integration

[![Install Bot](https://img.shields.io/badge/GitHub-Install%20Bot-black?style=flat-square&color=4ecdc4&logo=GitHub&logoColor=white)](https://github.com/apps/aladdinai-bot)
[![OpenCollective](https://img.shields.io/opencollective/all/aladdinai?style=flat-square&color=4ecdc4&logo=opencollective&logoColor=white)](https://opencollective.com/aladdinai)
[![GitHub stars](https://img.shields.io/github/stars/aliyevaladddin/AladdinAI?style=square&color=4ecdc4&logo=git&logoColor=white)](https://github.com/aliyevaladddin/AladdinAI)


<div align="middle">

<br/>

```
 █████╗ ██╗      █████╗ ██████╗ ██████╗ ██╗███╗   ██╗ █████╗ ██╗
██╔══██╗██║     ██╔══██╗██╔══██╗██╔══██╗██║████╗  ██║██╔══██╗██║
███████║██║     ███████║██║  ██║██║  ██║██║██╔██╗ ██║███████║██║
██╔══██║██║     ██╔══██║██║  ██║██║  ██║██║██║╚██╗██║██╔══██║██║
██║  ██║███████╗██║  ██║██████╔╝██████╔╝██║██║ ╚████║██║  ██║██║
╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═════╝ ╚═════╝ ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝
```

### Your AI agents. *Your infrastructure.* Your rules.

*AladdinAI is an open-source, self-hosted AI workspace —*
*agents, memory, CRM, and multi-channel messaging running entirely in your own infrastructure.*

<br/>

[![License](https://img.shields.io/badge/license-Apache%202.0-4ecdc4?style=flat-square&logo=Apache&logoColor=white)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-4ecdc4?style=flat-square&logo=docker&logoColor=white)](https://ghcr.io/aliyevaladddin/aladdinai)
[![Node](https://img.shields.io/badge/node-18%2B-4ecdc4?style=flat-square&logo=node.js&logoColor=white)](https://nodejs.org)
[![MongoDB for Startups](https://img.shields.io/badge/MongoDB-for%20Startups-4ecdc4?style=flat-square&logo=mongodb&logoColor=white)](https://www.mongodb.com/startups)
[![Issues](https://img.shields.io/github/issues/aliyevaladddin/AladdinAI?style=flat-square&color=4ecdc4&logo=socket&logoColor=white)](https://github.com/aliyevaladddin/AladdinAI/issues)
[![NPM Version](https://img.shields.io/npm/v/aladdin-ai?style=flat-square&color=4ecdc4&logo=npm&logoColor=white)](https://www.npmjs.com/package/aladdin-ai)


<br/>

| `436` unique cloners | `14` days since launch | `$0` marketing spend |
|:---:|:---:|:---:|
| **organic traction** | **after public release** | **zero paid promotion** |

<br/>

<div align="center">
  <img src="docs/demo.svg" alt="AladdinAI terminal demo" width="700"/>
</div>

**One command. No git clone. No Python. No Node toolchain. Just Docker.**

<br/>

</div>

---

## ◈ What is AladdinAI?

We believe the next wave of AI adoption won't happen in shared clouds. It will happen in companies that need **control over their data, their models, and their customer relationships.**

AladdinAI is the platform that makes that possible — without building everything from scratch.

> **Status:** actively developed. Most features are wired end-to-end and usable locally. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full picture.

---
 
## ◈ What's inside

| Module | Description |
|---|---|
| **Agents** | Per-user agents with their own model, system prompt, tool set, and safety stack (NemoGuard / Llama-Guard, PII redaction via GLiNER) |
| **Memory** | Private + shared stores with vector search (MongoDB Atlas + NIM embeddings). Every recall and write decision is logged via pluggable Gates |
| **CRM** | Contacts, deals, activities. Every inbound message is auto-attributed to a contact and logged to the activity timeline |
| **Orders & Sales** | Product catalog, orders with line items and a validated delivery lifecycle (`pending → delivered`), sales/marketing metrics (revenue, funnel, attribution), and `sales`-role agent tools that place and move orders. See [`docs/guides/ORDERS.md`](docs/guides/ORDERS.md) |
| **Channels** | Telegram, WhatsApp (Cloud API), SMS, IMAP/SMTP email. Outgoing webhooks for fan-out |
| **Voice** | Speak to agents and hear replies — browser capture → NVIDIA Riva ASR, optional TTS voice responses |
| **Documents** | Upload PDF, Excel (`.xlsx`), CSV, JSON, and text — auto-chunked and indexed into vector memory for recall |
| **Office tools** | Agents read and write real files via tools — Excel (`excel_*`) and outbound email (`send_email` over SMTP) |
| **Terminal** | Browser-based terminals (ttyd local shell, wetty SSH) for remote server management |
| **Triggers** | Cron-scheduled fan-out tasks via APScheduler, per-agent model overrides, fallback chains across providers |
| **Infrastructure** | Manage LLM providers, MongoDB clusters, cloud VMs (SSH), and BentoML deployments from the UI |

---
## ◈ How memory works

![Memory architecture](docs/memory_architecture.svg)

Every fact is evaluated by NemoGuard before it is written.  
Retrieval uses MongoDB Atlas Vector Search — semantic, not keyword.
---
## ◈ Built on sovereign-grade open infrastructure

<br/>

> **NVIDIA NIM** — LLM inference and embeddings on-prem or in any cloud. No dependency on shared inference APIs. Every agent routes to a NIM endpoint, making the entire inference layer sovereign by default.

> **MongoDB Atlas** — Long-term agentic memory with Atlas Vector Search. Handles both structured data (CRM, activity timelines) and the vector layer (semantic memory recall) in a single platform. No separate vector DB to sync.
> 
> *Backed by [MongoDB for Startups](https://www.mongodb.com/startups) — $500 in Atlas credits to remove infrastructure barriers for the first 8 months.*

> **BentoML** — Deploy and scale custom tools and local LLMs within your own infrastructure. Swap, scale, or version models directly from the AladdinAI UI — without touching the codebase.

---

## ◈ Quick start

One command — pulls prebuilt images from GHCR (multi-arch: `amd64` + `arm64`), generates a `.env` with cryptographically-secure secrets, and brings up the full stack:

```bash
npx aladdin-ai
```

```
✓ Services running
  Frontend: http://localhost:3000
  Backend:  http://localhost:8000
```

Open `http://localhost:3000`, register a user, and land on the dashboard.
Add at least one **LLM Provider** under *Settings → LLM Providers* before creating agents.

### Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS / Windows) or `docker` + `docker compose` (Linux)
- Node.js 18+ (just to run `npx`)

### Day-to-day commands

```bash
npx aladdin-ai up               # start services
npx aladdin-ai down             # stop services
npx aladdin-ai restart backend  # restart one service
npx aladdin-ai logs -f          # tail logs
npx aladdin-ai update           # pull latest images and recreate
npx aladdin-ai doctor           # diagnose setup issues
```

See [`cli/README.md`](cli/README.md) for the full command reference.

---

## ◈ Development setup

For contributors who want to modify the code rather than just run it:

```bash
npx aladdin-ai init --source
# or manually:
git clone https://github.com/aliyevaladddin/AladdinAI.git
cd AladdinAI
cp .env.example .env
docker compose up --build
```

For a non-Docker workflow with hot-reload:

```bash
make install           # creates .venv, installs Python deps
cd frontend && npm install && cd ..
make migrate           # apply Alembic migrations
make dev-backend       # FastAPI on :8000 with --reload
make dev-frontend      # Next.js on :3000 with --reload
```

---

## ◈ Tech stack

| Layer | Tools |
|---|---|
| **Frontend** | Next.js 15, React 19, TailwindCSS, shadcn/ui, sonner |
| **Backend** | FastAPI, SQLAlchemy 2 (async), Alembic, APScheduler |
| **Storage** | SQLite or Postgres (relational), MongoDB Atlas (vectors) |
| **LLM access** | Provider-agnostic — NIM, OpenAI, Anthropic, local via BentoML |
| **Auth** | JWT (HS256) with access + refresh tokens |
| **Realtime** | Server-sent events for chat streaming |

---

## ◈ Roadmap

- **Marketplace** — shareable agent templates, tool packs, and gate configurations
- **Multi-tenant SaaS mode** — deploy AladdinAI as a hosted service for your own customers, with per-tenant isolation and billing hooks
- **Advanced observability** — full trace view per agent turn: memory reads, gate decisions, tool calls, model latency
- **Expanded channels** — native mobile push, browser extension
- **One-click cloud deploy** — pre-configured Terraform modules for AWS, GCP, and Azure. Full stack up in under 10 minutes

---

## ◈ Repository layout

```
AladdinAI/
├── backend/          FastAPI service, models, services, tools, migrations
├── frontend/         Next.js 15 dashboard
├── scripts/          dev / install / migration helpers
├── docs/             Architecture & design notes
├── cli/              npx aladdin-ai CLI
├── docker-compose.yml
├── Makefile
└── .env.example
```

| Subtree | README |
|---|---|
| `backend/` | [Request lifecycle, services, how to add a tool/gate/channel](backend/README.md) |
| `frontend/` | [Page structure, panel pattern, API client](frontend/README.md) |
| `scripts/` | [What each shell script does](scripts/README.md) |
| `docs/` | [Architecture concept doc](docs/ARCHITECTURE.md) |

---

## ◈ Common make targets

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

## ◈ Production notes

- **`JWT_SECRET`** — replace with `openssl rand -hex 32` before deploying. Anyone who knows it can mint tokens for any user.
- **Database** — switch `DATABASE_URL` to Postgres. SQLite is fine locally but not for multi-worker deployments.
- **Frontend URL** — set `NEXT_PUBLIC_API_URL` to the public backend URL the browser will reach.
- **API keys** — provider keys live in the database (encrypted at rest, set via the UI), not in `.env`.

---

## ◈ Operations

### Logs

```bash
npx aladdin-ai logs -f             # tail all services
npx aladdin-ai logs -f backend     # backend only
npx aladdin-ai logs -f frontend    # frontend only
```

Every agent turn is traceable: memory reads, gate decisions, tool calls, and model latency are logged to the backend. Use `GET /api/agents/{agent_id}/gate-logs` to pull structured decision logs per agent.

### Upgrades

```bash
npx aladdin-ai update              # pull latest images, recreate containers
make migrate                       # apply any new database migrations
```

Images are versioned and tagged. The CLI always pulls the same tag it was installed with unless you pass `--tag latest` explicitly. Database migrations run automatically on backend startup via Alembic.

### Failure recovery

If a service crashes, Docker Compose restarts it automatically (`restart: unless-stopped`). To restart manually:

```bash
npx aladdin-ai restart backend
npx aladdin-ai restart frontend
npx aladdin-ai doctor              # diagnose config, DB connection, and provider health
```

Agent tasks (scheduled cron jobs via APScheduler) are in-process and will restart with the backend. Persistent state lives in Postgres — no in-memory-only state that can be lost on restart.

### Permissions

All resources are scoped **per user**. Agents, memories, CRM contacts, and channel connections are isolated by `user_id` at the database query level — a user cannot read or write another user's data even if they share the same instance.

Role model: `admin` users can manage LLM providers and system-wide settings. Regular users manage only their own agents and data.

### Agent limits

Agents are bounded at multiple layers to prevent runaway behaviour:

| Layer | Mechanism |
|---|---|
| **Safety gates** | NemoGuard / Llama-Guard runs before and after every model response. Blocks or redacts harmful content. |
| **PII redaction** | GLiNER-based extraction strips personal data from memory writes and shared context. |
| **Gate logging** | Every gate decision is written to `gate_logs` — auditable, queryable via API. |
| **Tool scope** | Each agent has an explicit tool list. No agent can call a tool it was not granted. |
| **Model overrides** | Per-agent model, temperature, and token limits are set at creation time and not changeable by the agent itself. |
| **Cron throttling** | Scheduled tasks are defined with explicit intervals — no self-scheduling or infinite loops. |

Configure gates under *Settings → Safety* in the dashboard.

---

## ◈ Terminal providers

Two browser-based terminal providers, running in isolated Docker containers with Traefik routing and forward-auth:

**ttyd** — Lightweight Bash/Zsh terminal in the browser. Minimal resource usage. Default for local access.

**wetty** — SSH-in-browser with server-side proxy. Password and key-based auth. Connects to remote Linux/Unix servers with automatic VM credential injection.

Install through the UI under *Settings → Terminal Providers*. No additional setup required.

---


## ◈ Feedback

I'm building AladdinAI in public and I read every message personally. Even one sentence helps — especially the negative ones.

- **Quick form:** https://aliyev.site/AladdinAI/feedback
- **Email:** aladdin@aliyev.site
- **GitHub:** [open an issue](https://github.com/aliyevaladddin/AladdinAI/issues/new) · [start a discussion](https://github.com/aliyevaladddin/AladdinAI/discussions)

*"This is broken." "Didn't get past step 2." "Cool but not for me." All of it useful.*

— Aladdin

---

## ◈ License

Apache 2.0 — see [LICENSE](LICENSE).

<div align="center">
<br/>

*Your data. Your models. Your rules.*

<br/>
</div>
