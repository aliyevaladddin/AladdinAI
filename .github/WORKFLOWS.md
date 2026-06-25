// NOTICE: This file is protected under RCF-PL
# .github — GitHub Configuration

This directory contains all GitHub-specific automation: CI/CD workflows,
bot integrations, Dependabot, issue templates, and AI agents.

---

## Workflows

| File | Trigger | What it does |
|---|---|---|
| [`ci.yml`](workflows/ci.yml) | push / PR → `main` | Lints Python (`ruff`), runs backend pytest + frontend jest, validates docker-compose |
| [`release.yml`](workflows/release.yml) | Release published via GitHub UI | Bumps `package.json` versions, runs `npm audit fix` on frontend, publishes CLI to npm |
| [`docker-publish.yml`](workflows/docker-publish.yml) | push `v*` tag / manual | Builds `aladdinai-backend` and `aladdinai-frontend` Docker images, pushes to GHCR (`linux/amd64` + `linux/arm64`) |
| [`changelog.yml`](workflows/changelog.yml) | push → `main` or `v*` tag | Generates `CHANGELOG.md` via `git-cliff`, opens a bot PR with auto-merge enabled |
| [`generate-docs.yml`](workflows/generate-docs.yml) | push → `main` (backend changed) / manual | Generates `docs/openapi.json` + `docs/API.md`, opens a bot PR with auto-merge enabled |
| [`cli-publish.yml`](workflows/cli-publish.yml) | push `cli-v*` tag / manual | Publishes `aladdin-ai` package to npm; supports dry-run via `workflow_dispatch` |
| [`code-review.yml`](workflows/code-review.yml) | PR opened / updated | NVIDIA Code Review bot reviews the diff and posts a comment via NIM LLM |
| [`rcf-audit.yml`](workflows/rcf-audit.yml) | push → `main` / PR | Runs RCF Protocol compliance security audit |
| [`webpack.yml`](workflows/webpack.yml) | push / PR → `main` | Installs frontend deps and runs `next build` to catch build errors early |
| [`bot-commits.yml`](workflows/bot-commits.yml) | manual (`workflow_dispatch`) | Demo workflow — creates an activity log commit via `AladdinAI[bot]` and `NVIDIA Code Review[bot]` |

### Release flow (end-to-end)

```
GitHub UI → Publish Release (tag v*.)
        │
        ├─▶ release.yml       — bump versions, npm audit fix, publish CLI to npm
        ├─▶ docker-publish.yml — build & push backend + frontend images to GHCR
        └─▶ changelog.yml      — regenerate CHANGELOG.md
```

---

## Bots

Two GitHub Apps are registered and used across workflows.

### AladdinAI\[bot\]

Used for automated commits, changelog PRs, and documentation PRs.
Commits appear under the `AladdinAI[bot]` identity so they are distinct
from human commits and can be filtered in the log.

| Secret | Description |
|---|---|
| `ALADDINAI_BOT_APP_ID` | GitHub App ID |
| `ALADDINAI_BOT_PRIVATE_KEY` | GitHub App private key (PEM) |

### NVIDIA Code Review\[bot\]

Posts AI-powered code review comments on every PR using a NIM-hosted LLM.

| Secret | Description |
|---|---|
| `NVIDIA_BOT_APP_ID` | GitHub App ID |
| `NVIDIA_BOT_PRIVATE_KEY` | GitHub App private key (PEM) |
| `NIM_API_KEY` | NVIDIA NIM API key |
| `NIM_BASE_URL` | NIM inference endpoint URL |
| `NIM_MODEL` | Model name to use for review (e.g. `meta/llama-3.1-70b-instruct`) |

Setup instructions: [GITHUB_APP_SETUP.md](GITHUB_APP_SETUP.md)

---

## Dependabot

[`dependabot.yml`](dependabot.yml) configures automatic dependency update PRs:

| Ecosystem | Directory | Schedule |
|---|---|---|
| npm (CLI) | `/` | weekly |
| npm (Frontend) | `/frontend` | weekly — patches grouped into one PR |
| pip (Backend) | `/` | weekly |
| GitHub Actions | `/` | weekly |

Frontend patch updates are grouped under the `security-patches` group so
they arrive as a single PR rather than one per package.

---

## Agents

[`agents/`](agents/) contains Python scripts run inside workflows:

| Script | Used by |
|---|---|
| `code_review_agent.py` | `code-review.yml` — fetches the PR diff and calls NIM LLM to produce a review comment |

---

## Required Secrets

All secrets are set under **Settings → Secrets and variables → Actions**.

| Secret | Required by |
|---|---|
| `ALADDINAI_BOT_APP_ID` | `changelog.yml`, `generate-docs.yml`, `bot-commits.yml` |
| `ALADDINAI_BOT_PRIVATE_KEY` | `changelog.yml`, `generate-docs.yml`, `bot-commits.yml` |
| `NVIDIA_BOT_APP_ID` | `code-review.yml`, `bot-commits.yml` |
| `NVIDIA_BOT_PRIVATE_KEY` | `code-review.yml`, `bot-commits.yml` |
| `NIM_API_KEY` | `code-review.yml` |
| `NIM_BASE_URL` | `code-review.yml` |
| `NIM_MODEL` | `code-review.yml` |
| `NPM_API_TOKEN` | `release.yml`, `cli-publish.yml` |
| `RCF_LICENSE_KEY` | `rcf-audit.yml` |

---

## Issue Templates

[`ISSUE_TEMPLATE/bug_report.md`](ISSUE_TEMPLATE/bug_report.md) — standard
bug report form with reproduction steps, environment info, and screenshots.

---

## See also

- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — commit format, PR process, branch naming
- [`SECURITY.md`](../SECURITY.md) — vulnerability disclosure policy
- [`CODE_OF_CONDUCT.md`](../CODE_OF_CONDUCT.md) — community guidelines
- [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) — system architecture overview
