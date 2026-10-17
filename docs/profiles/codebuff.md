# Codebuff (Buffy)

> Security hardening, reliability fixes, and dashboard polish for AladdinAI.

## Role

Codebuff is an AI coding agent by [Codebuff](https://codebuff.com). In this repository it commits as **Buffy**. It contributed to AladdinAI through security audits, bug fixes, refactoring, and tests.

## Contributions

### Security Hardening
- SSH `known_hosts=None` → TOFU verification (MITM protection, issue #356)
- `json.loads` safety, input validation, Pydantic V2 `ConfigDict`
- Silent exception swallowing → proper logging
- Rate limiting and error boundaries

### Reliability
- DuckDuckGo search returning 0 web results — fixed
- API cache invalidation on POST / PUT / PATCH / DELETE (`invalidateMutated` helper)
- Docker build: python symlink and env for `node-gyp`
- Hydration error from nested buttons in trace panels

### Features & UI
- Tracing toggle, global traces page, trace feedback, Self-Forging UI
- Chat streaming without re-rendering the whole message list
- Fixed broken design tokens, dashboard UI polish (VoicePlayer, TabBar, reports colors)

### Tests & Docs
- CRM router tests (contacts, deals, products, orders)
- Agent Sandbox architecture guide
- Updated Architecture, Testing, and Backend docs

## Stats

| Metric | Value |
|--------|-------|
| Commits | 23 |
| Active | 2026-08-18 |

## Links

- [Codebuff](https://codebuff.com) — AI coding agent
- [Freebuff](https://freebuff.com) — free AI coding tool
