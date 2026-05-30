# Contributing to AladdinAI

First off, thank you for considering contributing to AladdinAI! It's people like you that make AladdinAI a great sovereign platform.

## Code of Conduct
By participating in this project, you agree to maintain a respectful and collaborative environment. We value constructive feedback, technical excellence, and alignment with the project's sovereign principles.

## How Can I Contribute?

### Reporting Bugs
* Check the [existing issues](https://github.com/aliyevaladddin/AladdinAI/issues) to see if the bug has already been reported.
* Use a clear and descriptive title for the issue.
* Describe the exact steps which reproduce the problem.
* Include your environment details (OS, Docker version, browser).
* Include screenshots, terminal logs, or network traces if possible.

### Suggesting Enhancements
* Explain how the enhancement would benefit the "Sovereign Tech" ecosystem.
* Provide specific examples of use cases.
* Consider whether the feature aligns with AladdinAI's core principles (see below).

### Pull Requests
1. Fork the repo and create your branch from `main`.
2. Follow the [conventional commits](#git-commit-messages) format.
3. If you've added code that should be tested, add tests.
4. If you've changed APIs, update the documentation.
5. Ensure the test suite passes (`pytest` for backend, `npm test` for frontend).
6. Make sure your code follows the existing style:
   - **Backend**: FastAPI, Pydantic models, type hints
   - **Frontend**: Next.js App Router, TailwindCSS, TypeScript
   - **CLI**: TypeScript, Commander.js

## Development Setup

### Prerequisites
- **Python 3.11+** (backend)
- **Node.js 18+** (frontend, CLI)
- **Docker & Docker Compose** (full stack)
- **Git** with GPG signing configured (optional but recommended)

### Quick Start

**Option 1: Full stack with Docker**
```bash
npx aladdin-ai
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
```

**Option 2: Local development**

Backend:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:
```bash
cd frontend
npm install
npm run dev
# Opens on http://localhost:3000
```

CLI:
```bash
cd cli
npm install
npm run build
npm link  # Makes `aladdin-ai` available globally
```

### Project Structure
```
AladdinAI/
├── backend/          # FastAPI backend
│   ├── app/
│   │   ├── models/   # SQLAlchemy + Pydantic models
│   │   ├── routers/  # API endpoints
│   │   ├── services/ # Business logic (memory, safety, RCF)
│   │   └── tools/    # Agent tools registry
│   └── alembic/      # Database migrations
├── frontend/         # Next.js frontend
│   └── src/app/
│       └── (dashboard)/dashboard/  # Main UI pages
├── cli/              # Node.js CLI (npx aladdin-ai)
└── docs/             # Architecture docs
```

### Running Tests

Backend:
```bash
cd backend
pytest
```

Frontend:
```bash
cd frontend
npm test
```

## Styleguides

### Git Commit Messages
We use **conventional commits** for automatic changelog generation via [git-cliff](https://git-cliff.org/).

Format: `<type>: <description>`

**Types:**
- `feat:` — new feature
- `fix:` — bug fix
- `perf:` — performance improvement
- `docs:` — documentation only
- `chore:` — maintenance (skipped in changelog)
- `test:` — adding or updating tests
- `refactor:` — code change that neither fixes a bug nor adds a feature

**Examples:**
```
feat: add GitHub webhook integration for bot triggers
fix: resolve race condition in memory extraction
docs: update CONTRIBUTING.md with conventional commits
chore: bump dependencies to latest versions
```

### Code Style
- **Python**: Follow PEP 8, use type hints, prefer Pydantic models
- **TypeScript**: Use strict mode, prefer functional components
- **CSS**: Use TailwindCSS utility classes, avoid custom CSS when possible

## Sovereign Principles
Every contribution should align with the core principles of **Sovereignty**:

1. **Zero unnecessary dependencies** — Prefer standard library and well-established packages over trendy frameworks.
2. **Privacy by default** — User data stays in user infrastructure. No telemetry, no tracking, no phone-home.
3. **Self-hosted first** — Every feature must work without external SaaS dependencies.
4. **High-fidelity UX** — Premium feel, fast interactions, thoughtful design.
5. **Transparent security** — Open source, auditable, no obfuscation.

## Questions?
Open a [discussion](https://github.com/aliyevaladddin/AladdinAI/discussions) or reach out via issues. We're here to help.
