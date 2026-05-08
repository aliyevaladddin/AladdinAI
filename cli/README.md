# aladdin-ai

Bootstrap a local AladdinAI instance with one command.

```bash
npx aladdin-ai
```

Clones the repo, copies `.env`, installs backend (creates `.venv`) and
frontend dependencies, and applies database migrations. After it finishes:

```bash
cd aladdin-ai
make dev-backend    # FastAPI on :8000
make dev-frontend   # Next.js on :3000
```

## Options

```
npx aladdin-ai [options]

  -n, --name <name>     project directory (default: aladdin-ai)
  -y, --yes             accept defaults, skip prompts
      --skip-install    clone only, don't install deps or migrate
  -V, --version
  -h, --help
```

## Requirements

- Node.js 20+
- Python 3.11+
- `make`, `git`
- (optional) Docker — only if you want to use Postgres instead of the default SQLite

## What is AladdinAI?

A self-hosted AI workspace: agents with private + shared memory, CRM,
multi-channel messaging (Telegram / WhatsApp / SMS / email), cron triggers,
and provider-agnostic LLM routing. See the
[main repo](https://github.com/aliyevaladddin/AladdinAI) for the full story.

## License

Apache-2.0
