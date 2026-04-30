# AladdinAI

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-teal.svg)](https://fastapi.tiangolo.com)

AI Agent BYOI (Bring Your Own Infrastructure) Platform.

Connect your own cloud VMs, LLM providers (NVIDIA NIM, OpenAI, Anthropic, Ollama), MongoDB, and BentoML — then create and manage AI agents visually.

## Stack

- **Frontend**: Next.js 16 + TypeScript + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI + SQLAlchemy + Alembic + asyncpg
- **Database**: PostgreSQL (platform data) + user-connected MongoDB (agent data)
- **Auth**: JWT (access + refresh tokens)

## Features

- 🔌 **Connect your own LLM providers** — NVIDIA NIM, OpenAI, Anthropic, Ollama, custom endpoints
- 🖥️ **Connect your own VMs** — SSH-based real connection testing with asyncssh
- 🤖 **Build AI Agents** — create, configure and manage agents visually
- 💬 **Chat interface** — talk to your agents with full conversation history
- 🔗 **Channels** — Email, messaging integrations and webhooks
- 📊 **Built-in CRM** — contacts, deals, and activity tracking
- 🗄️ **MongoDB integration** — bring your own database for agent data
- ⚡ **BentoML support** — connect your own ML model serving

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

## Contributing

Contributions are welcome! Feel free to open issues and pull requests.

1. Fork the repository
2. Create your feature branch (`git checkout -b feat/your-feature`)
3. Commit your changes (`git commit -m 'feat: add your feature'`)
4. Push to the branch (`git push origin feat/your-feature`)
5. Open a Pull Request

## License

This project is licensed under the Apache License 2.0 — see the [LICENSE](LICENSE) file for details.

Copyright 2026 Aladdin Aliyev
