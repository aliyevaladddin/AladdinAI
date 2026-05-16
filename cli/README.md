# aladdin-ai

Self-hosted AI workspace, one command to install and run.

```bash
npx aladdin-ai
```

This clones the repo, generates a `.env` with cryptographically-secure
secrets (`JWT_SECRET`, `FERNET_KEY`, `POSTGRES_PASSWORD`), and brings up
the stack with Docker Compose. After it finishes, open
[http://localhost:3000](http://localhost:3000).

## Commands

```bash
npx aladdin-ai                # alias for `init`
npx aladdin-ai init           # bootstrap a new project here
npx aladdin-ai up             # start services (docker compose up -d)
npx aladdin-ai up --build     # rebuild images first
npx aladdin-ai down           # stop services
npx aladdin-ai down -v        # also wipe volumes (destructive)
npx aladdin-ai restart        # restart everything
npx aladdin-ai restart backend
npx aladdin-ai logs           # tail all service logs
npx aladdin-ai logs backend -f
npx aladdin-ai doctor         # diagnose setup issues
```

All commands except `init` look for the nearest `docker-compose.yml` and
`backend/` directory above the current working directory, so you can run
them from anywhere inside a project.

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

## Requirements

- Node.js 18+
- Docker 20+ with the Compose plugin (`docker compose version` works)
- `git`

No local Python, Node toolchain, or `make` needed — everything runs in
containers.

## What is AladdinAI?

A self-hosted AI workspace: agents with private + shared memory, CRM,
multi-channel messaging (Telegram / WhatsApp / SMS / email), cron
triggers, and provider-agnostic LLM routing. See the
[main repo](https://github.com/aliyevaladddin/AladdinAI) for the full
story.

## Releasing

Publishing is fully automated via GitHub Actions
(`.github/workflows/cli-publish.yml`). The token lives in the repo's
`NPM_API_TOKEN` secret — never run `npm publish` locally.

```bash
# 1. Bump the version inside cli/package.json
cd cli
npm version patch              # or minor / major
cd ..

# 2. Commit and tag (prefix MUST be cli-v<version>)
git commit -am "cli: bump to $(node -p "require('./cli/package.json').version")"
git tag "cli-v$(node -p "require('./cli/package.json').version")"
git push origin main --tags
```

The workflow triggers on the `cli-v*` tag, verifies the tag matches
`package.json`, smoke-tests `--help`, and runs `npm publish`. Run it
manually from the Actions tab with **Dry run** enabled to rehearse
without publishing.

## License

Apache-2.0
