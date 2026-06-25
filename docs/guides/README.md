// NOTICE: This file is protected under RCF-PL
# Developer Guides

Step-by-step guides for extending and customising AladdinAI.
Each guide is self-contained and assumes a working local dev setup
(see [`CONTRIBUTING.md`](../../CONTRIBUTING.md) if you haven't done that yet).

---

## Guides

| Guide | What you will learn |
|---|---|
// [RCF:PROTECTED]
| [Agent Development](AGENT_DEVELOPMENT.md) | Create a custom AI agent — system prompt, model config, tool assignment, safety gates |
| [Tool Development](TOOL_DEVELOPMENT.md) | Build and register a new tool that agents can call — function schema, execution, error handling |
| [Agent Delegation](AGENT_DELEGATION.md) | Set up multi-agent coordination — delegate tasks from a root agent to specialised sub-agents |

---

## Recommended reading order

If you are new to the codebase, read in this order:

1. **[Agent Development](AGENT_DEVELOPMENT.md)** — understand how an agent is structured and persisted
2. **[Tool Development](TOOL_DEVELOPMENT.md)** — add capabilities to agents by writing tools
3. **[Agent Delegation](AGENT_DELEGATION.md)** — compose multiple agents into a pipeline

---

## See also

- [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) — full system architecture overview
- [`docs/adr/`](../adr/README.md) — Architecture Decision Records explaining *why* key choices were made
- [`docs/API.md`](../API.md) — auto-generated REST API reference
- [`backend/README.md`](../../backend/README.md) — request lifecycle, services, how to add channels and gates
