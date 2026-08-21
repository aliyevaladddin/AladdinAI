# Antigravity

> Security hardening, refactoring, and bug fixes for AladdinAI.

## Role

Antigravity is an AI coding agent powered by [Codebuff](https://codebuff.com) / [Freebuff](https://freebuff.com). It contributes to AladdinAI through code reviews, security audits, refactoring, and automated testing.

## Contributions

### Security Hardening
- CRM contacts import: added 10 MB upload size limit
- `json.loads` protection with `_safe_json()` helper (6 call sites)
- Silent exception swallowing → proper logging
- SSH known_hosts TOFU model (MITM protection)
- Rate limiting on auth, chat upload, and forging endpoints

### Reliability
- Error boundaries on dashboard pages (no more white screens)
- Readiness probe endpoint (`/ready`) for Docker/K8s
- `subprocess.run` → `asyncio.create_subprocess_exec` (non-blocking)
- DuckDuckGo search: HTML primary, Instant Answer as bonus

### Code Quality
- SQL playground refactored: 1255 → 454 lines (64% reduction)
- 46 stale branches merged and cleaned up
- `print()` → `log.warning()` in production code
- OpenAPI tags added to undocumented routers
- `<a>` → `<Link>` for Next.js client-side navigation

### Documentation
- Agent Sandbox guide (`AGENT_SANDBOX.md`)
- Updated Architecture, Testing, and Backend docs
- Contributors table with visual avatars

## Stats

| Metric | Value |
|--------|-------|
| Commits | 14+ |
| Files changed | 50+ |
| Tests added | 30+ |
| Issues closed | 20+ |
| Branches cleaned | 46 |

## Links

- [Codebuff](https://codebuff.com) — the platform Antigravity runs on
- [Freebuff](https://freebuff.com) — free AI coding tool
