# Antigravity

> Branch integration, type safety, and dashboard navigation for AladdinAI.

## Role

Antigravity is an agentic AI coding assistant built by the **Google DeepMind** team (Advanced Agentic Coding). It works as a pair programmer inside the IDE: it reads the codebase, runs commands, edits files, and verifies changes in the browser.

## Contributions

### Branch Integration
- Merged 15 feature/fix branches into `main` with conflict resolution
    - `fix/ssh-known-hosts-tofu` — kept CodeQL-safe test data
    - `feat/traces-forging-ui` — kept validation + accessibility
    - `feat/ui-polish-chat-perf` — kept theme tokens and count badges
    - `fix/critical-issues`, `fix/important-issues`, `fix/pydantic-exceptions-validation`, …

### Type Safety
- Removed 16 of 19 `type: ignore` suppressions in the backend

### Dashboard Navigation
- Moved **Traces** from sidebar → Settings › Observability
- Moved **Self-Forging** from sidebar → Settings › Training
- Fixed nested-button hydration error in agent traces panel
- Removed unused imports from `dashboard-nav`

### Bots & Integrations
- Qwen bot: resolve bot ID via public `/users` endpoint
- Qwen bot: direct push to `main` so it appears in contributors
- Telegram: fixed photo bytes handling
- `doctor`: added DB check

### Documentation
- Antigravity and Cursor contributor profiles

## Stats

| Metric | Value |
|--------|-------|
| Commits | 24 |
| Branches merged | 15 |
| Active | 2026-08-21 |

## Links

- [Google Antigravity](https://antigravity.google) — agentic IDE by Google
- [Google DeepMind](https://deepmind.google) — team behind Antigravity
