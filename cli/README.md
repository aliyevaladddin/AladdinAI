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

## Releasing

Publishing is fully automated via GitHub Actions
(`.github/workflows/cli-publish.yml`). The token lives in the repo's
`NPM_API_TOKEN` secret — never run `npm publish` locally.

```bash
# 1. Bump the version inside cli/package.json
cd cli
npm version patch          # or minor / major — updates package.json
cd ..

# 2. Commit and tag (tag prefix MUST be cli-v<version>)
git commit -am "cli: bump to $(node -p "require('./cli/package.json').version")"
git tag "cli-v$(node -p "require('./cli/package.json').version")"
git push origin main --tags
```

The workflow triggers on the `cli-v*` tag, verifies the tag matches
`package.json`, smoke-tests `--help`, and runs `npm publish`. Failures (tag
mismatch, version already on npm) fail the workflow safely without
publishing anything broken.

To rehearse without publishing, run the workflow manually from the Actions
tab with **Dry run** enabled.

## License

Apache-2.0
