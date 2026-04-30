# AladdinAI

AI Agent BYOI (Bring Your Own Infrastructure) Platform.

Connect your own cloud VMs, LLM providers (NVIDIA NIM, OpenAI, Anthropic, Ollama), MongoDB, and BentoML — then create and manage AI agents visually.

## Stack

- **Frontend**: Next.js 16 + TypeScript + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI + SQLAlchemy + Alembic + asyncpg
- **Database**: PostgreSQL (platform data) + user-connected MongoDB (agent data)
- **Auth**: JWT (access + refresh tokens)

## Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev

# Or with Docker
docker-compose up
```

## API Docs

Once backend is running: http://localhost:8000/docs
