// NOTICE: This file is protected under RCF-PL
# Developer Guides

Step-by-step guides for extending and customising AladdinAI.
Each guide is self-contained and assumes a working local dev setup
(see [`CONTRIBUTING.md`](../../CONTRIBUTING.md) if you haven't done that yet).

---

## Guides

| Guide | What you will learn |
|---|---|
| [Agent Development](AGENT_DEVELOPMENT.md) | Create a custom AI agent — system prompt, model config, tool assignment, safety gates |
| [Tool Development](TOOL_DEVELOPMENT.md) | Build and register a new tool that agents can call — function schema, execution, error handling |
| [Agent Delegation](AGENT_DELEGATION.md) | Set up multi-agent coordination — delegate tasks from a root agent to specialised sub-agents |
| [Orders & Sales](ORDERS.md) | Product catalog, orders with a delivery lifecycle, sales/marketing metrics, and the `sales`-role agent tools |
| [File Workspace](FILE_WORKSPACE.md) | Spaces & roles, append-only versions, audit timeline, the safe agent file-tools, and the `/dashboard/files` page |
| [Outgoing Webhooks](WEBHOOKS.md) | Push events to Zapier or any HTTP endpoint — event list, RCF signing, agent tools, edit/test from the UI |
| [Self-Forging](SELF_FORGING.md) | Freeze a golden set of labeled traces and run the base-vs-forged evaluation harness |
| [Agent Sandbox](AGENT_SANDBOX.md) | How agent code execution is isolated in Docker containers — creation, lifecycle, security, fallback |
| [Triggers & Automations](TRIGGERS_AUTOMATIONS.md) | Run agents on a schedule — presets, cron validation, manual runs, task templates |
| [Web Search](WEB_SEARCH.md) | Native zero-key meta-search — four engines, retries, synthesis endpoint, agent tool |
| [SQL Playground](SQL_PLAYGROUND.md) | Read-only SQL exploration for users — schema introspection and the layered security model |
| [Modular Terminal System](TERMINAL_SYSTEM.md) | Pluggable terminal providers — manifests, marketplace, sessions, token broker, SSH proxy |

---

## Recommended reading order

If you are new to the codebase, read in this order:

1. **[Agent Development](AGENT_DEVELOPMENT.md)** — understand how an agent is structured and persisted
2. **[Tool Development](TOOL_DEVELOPMENT.md)** — add capabilities to agents by writing tools
3. **[Triggers & Automations](TRIGGERS_AUTOMATIONS.md)** — schedule agents to work without supervision

---

## See also

- [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) — full system architecture overview
- [`docs/adr/`](../adr/README.md) — Architecture Decision Records explaining *why* key choices were made
- [`docs/API.md`](../API.md) — auto-generated REST API reference
- [`backend/README.md`](../../backend/README.md) — request lifecycle, services, how to add channels and gates
