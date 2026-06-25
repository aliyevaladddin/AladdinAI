// NOTICE: This file is protected under RCF-PL
# aladdin-ai

Self-hosted AI workspace, one command to install and run.

```bash
npx aladdin-ai
```

This drops a `docker-compose.yml` + a `.env` (filled with

cryptographically-secure `JWT_SECRET`, `FERNET_KEY`, `POSTGRES_PASSWORD`)
into a new directory, pulls the prebuilt images from GHCR, and starts
the stack. Open [http://localhost:3000](http://localhost:3000) when it
finishes.

No `git`, no source code on your machine, no Python or Node toolchain.
Just Docker.

## Install modes

| Mode | Command | What you get | Who it's for |
|---|---|---|---|
| Image (default) | `npx aladdin-ai` | compose + `.env` (~2 files), images pulled from GHCR | Anyone who just wants to use AladdinAI |
| Source | `npx aladdin-ai init --source` | Full git clone, images built locally | Contributors who want to modify the code |

Updates in image mode are one command: `npx aladdin-ai update`.

## Commands

```bash
npx aladdin-ai                  # alias for `init` (image mode)
npx aladdin-ai init             # bootstrap a new project here
npx aladdin-ai init --source    # bootstrap from git clone (for contributors)

npx aladdin-ai up               # start services (docker compose up -d)
npx aladdin-ai up --build       # rebuild images first (source mode)
npx aladdin-ai down             # stop services
npx aladdin-ai down -v          # also wipe volumes (DESTROYS data)
npx aladdin-ai restart          # restart everything
npx aladdin-ai restart backend  # restart one service

npx aladdin-ai logs             # tail all service logs
npx aladdin-ai logs backend -f  # follow one service

npx aladdin-ai update           # pull latest images and recreate services
npx aladdin-ai doctor           # diagnose setup issues
```

All commands except `init` find the nearest `docker-compose.yml` above
the current working directory, so you can run them from anywhere inside
a project.

## `doctor`

Quick health check when something feels off:

```
$ npx aladdin-ai doctor

Tooling
  ✓ git installed
  ✓ docker + compose available, daemon running

Project
  ✓ project root: /home/me/aladdin-ai
  ✓ .env has required keys

Ports
  ✓ port 3000 (frontend) listening
  ✓ port 8000 (backend) listening
  ✓ port 5432 (postgres) listening

Services
  ✓ backend: running
  ✓ frontend: running
  ✓ postgres: running

Reachability
  ✓ backend responding on http://localhost:8000 (HTTP 200)
  ✓ frontend responding on http://localhost:3000 (HTTP 200)

All critical checks passed.
```

It also flags `.env` files that still hold the example placeholders, so
you don't accidentally expose an instance with `JWT_SECRET=change-me`.

## Pinning to a specific version

By default the compose file pulls the `:latest` tag. To pin a release,
set `ALADDINAI_VERSION` in your `.env`:

```
ALADDINAI_VERSION=1.0.0
```

Then `npx aladdin-ai update` will only ever pull that version.

## Requirements

- Node.js 18+
- Docker 20+ with the Compose plugin (`docker compose version` works)
- `git` — only for `init --source`

## What is AladdinAI?

A self-hosted AI workspace: agents with private + shared memory, CRM,
multi-channel messaging (Telegram / WhatsApp / SMS / email), cron
triggers, and provider-agnostic LLM routing. See the
[main repo](https://github.com/aliyevaladddin/AladdinAI) for the full
story.

## Releasing

**CLI** (this package on npm) — publish via GitHub Actions
(`.github/workflows/cli-publish.yml`):

```bash
cd cli
npm version patch                # or minor / major
cd ..
git commit -am "cli: bump to $(node -p "require('./cli/package.json').version")"
git tag "cli-v$(node -p "require('./cli/package.json').version")"
git push origin main --tags
```

**Backend + frontend images** — publish to GHCR via
`.github/workflows/docker-publish.yml`:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The workflow builds both images for linux/amd64 + linux/arm64 and pushes
them as `ghcr.io/aliyevaladddin/aladdinai-backend:1.0.0`,
`ghcr.io/aliyevaladddin/aladdinai-frontend:1.0.0`, and `:latest`.

## License

Apache-2.0
