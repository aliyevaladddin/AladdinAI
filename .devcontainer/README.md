# AladdinAI — Dev Container

This directory configures a ready-to-code development environment for
[VS Code Dev Containers](https://code.visualstudio.com/docs/devcontainers/containers)
and [GitHub Codespaces](https://github.com/features/codespaces).

One click — full backend, frontend and Docker stack, no local setup required.

---

## What's inside

| Component | Details |
|---|---|
| **Base image** | `python:3.11-slim-bookworm` |
| **Node.js** | v22 (installed via Dev Container feature) |
| **Docker** | Docker-outside-of-Docker — reuses the host daemon |
| **Python deps** | All `backend/requirements.txt` packages pre-installed |
| **System tools** | `git`, `curl`, `wget`, `build-essential`, `libpq-dev` |
| **VS Code extensions** | `ms-python.python`, `ms-python.vscode-pylance` |
| **Port** | `8000` exposed (FastAPI backend) |

> The container runs as **root** so Docker socket access works without extra permission steps.

---

## Quick start

### VS Code Dev Containers

1. Install the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
2. Open the repo in VS Code
3. Press `F1` → **Dev Containers: Reopen in Container**
4. Wait for the build (~1–2 min on first run, cached after that)

### GitHub Codespaces

Click the green **Code** button on the repo → **Codespaces** → **Create codespace on main**.

---

## Starting the stack inside the container

Copy the environment file and bring up all services:

```bash
cp .env.example .env
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend (Next.js) | http://localhost:3000 |
| Backend (FastAPI) | http://localhost:8000 |
| API docs | http://localhost:8000/docs |

### Hot-reload development (no Docker)

```bash
make install          # create .venv, install Python deps
cd frontend && npm install && cd ..
make migrate          # apply Alembic migrations
make dev-backend      # FastAPI on :8000 with --reload
make dev-frontend     # Next.js on :3000 with --reload
```

---

## Docker socket (OrbStack / Docker Desktop)

The `devcontainer.json` mounts the OrbStack socket by default:

```json
{
  "source": "${localEnv:HOME}/.orbstack/run/docker.sock",
  "target": "/var/run/docker.sock"
}
```

If you use **Docker Desktop** instead of OrbStack, replace the `source` with:

```
/var/run/docker.sock
```

After the container starts, socket permissions are fixed automatically via `postCreateCommand`.

---

## Files

| File | Purpose |
|---|---|
| `devcontainer.json` | Container name, features, VS Code extensions, post-create hook |
| `Dockerfile` | Base image, system packages, Python deps, exposed port |
| `README.md` | This file |

---

## See also

- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — coding conventions, commit format, PR process
- [`Makefile`](../Makefile) — all available `make` targets
- [`docker-compose.yml`](../docker-compose.yml) — full service definitions
