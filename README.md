# AladdinAI

A self-hosted AI workspace that brings agents, CRM, multi-channel messaging,
and infrastructure controls under one roof. Configure agents with tools and
private/shared memory, route LLM traffic across providers, schedule recurring
tasks, and ingest conversations from Telegram / WhatsApp / SMS / email — all
from a single Next.js dashboard backed by a FastAPI service.

> Status: actively developed. Most features below are wired end-to-end and
> usable locally; some surfaces (webhook triggers, BentoML deploy targets,
> design polish) are still evolving. See `docs/ARCHITECTURE.md` for the full
> picture.

---

## What's inside

- **Agents** — create per-user agents with their own model, system prompt,
  tool set (CRM, inter-agent delegation, memory), and safety stack.
- **Memory** — per-agent private store + cross-agent shared store, vector
  search via MongoDB Atlas + NIM embeddings, automatic per-message extraction.
- **Gates** — pluggable decision points around handoffs, memory writes, and
  recall reranking. Every decision is logged.
- **Safety** — ingress/egress moderation (NemoGuard / Llama-Guard) and PII
  redaction (GLiNER) configurable per agent and per phase.
- **CRM** — contacts, deals, activities. Inbound messages from any channel
  are auto-attributed to a contact and written to the activity timeline.
- **Channels** — Telegram, WhatsApp (Cloud API), SMS providers, IMAP/SMTP
  email accounts. Outgoing webhooks for fan-out.
- **Triggers** — cron-scheduled fan-out tasks delivered to one or more agents
  (powered by APScheduler).
- **Routing** — choose default models, per-agent overrides, fallback chains.
- **Infrastructure** — manage LLM provider connections, MongoDB clusters,
  cloud VMs (SSH), and BentoML deployments from the UI.

---

## Quick start

```bash
# 1. Clone & enter the repo
git clone https://github.com/<you>/AladdinAI.git
cd AladdinAI

# 2. Copy env template
cp .env.example .env
# Edit .env — at minimum, set JWT_SECRET in production.

# 3. Install backend (creates .venv) and frontend deps
make install
cd frontend && npm install && cd ..

# 4. Apply database migrations
make migrate

# 5. Run both services (in two terminals)
make dev-backend    # FastAPI on http://localhost:8000
make dev-frontend   # Next.js on http://localhost:3000
```

Open `http://localhost:3000`, register a user, and you'll land on the
dashboard. Add at least one **LLM Provider** (Settings → LLM Providers) before
creating agents — NVIDIA NIM works out of the box with a free API key.

By default the backend uses SQLite (`backend/aladdinai.db`). To switch to
Postgres, uncomment `DATABASE_URL` in `.env` and run
`docker compose up postgres -d`.

---

## Tech stack

| Layer       | Tools                                                       |
|-------------|-------------------------------------------------------------|
| Frontend    | Next.js 15, React 19, TailwindCSS, shadcn/ui, sonner        |
| Backend     | FastAPI, SQLAlchemy 2 (async), Alembic, APScheduler         |
| Storage     | SQLite or Postgres (relational), MongoDB Atlas (vectors)    |
| LLM access  | Provider-agnostic (NIM, OpenAI, Anthropic, local via BentoML) |
| Auth        | JWT (HS256) with access + refresh tokens                    |
| Realtime    | Server-sent events for chat streaming                       |

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

- Replace `JWT_SECRET` with `openssl rand -hex 32`. Anyone who knows it can
  mint tokens for any user.
- Switch `DATABASE_URL` to Postgres. SQLite is fine locally but not for
  multi-worker deployments.
- Set `NEXT_PUBLIC_API_URL` to the public backend URL the browser will reach.
- Provider API keys live in the database (encrypted at rest, set via the UI),
  not in `.env`.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
