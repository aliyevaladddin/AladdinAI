// NOTICE: This file is protected under RCF-PL
# Triggers & Automations

Triggers run agents on a schedule without human interaction — the backbone
of AladdinAI's autonomous behaviour (daily digests, periodic sweeps, follow-ups).

---

## Concepts

| Concept | What it is |
|---|---|
| **AgentTrigger** | A named schedule bound to one or more agents, with a task template |
| **Preset** | Human-friendly schedule shortcut (`resolve_preset`) instead of raw cron |
| **Run** | One execution: the trigger materialises `task_template` (+ optional context) and dispatches it to each agent |

---

## Schedules

Two kinds:

```json
{ "schedule_kind": "preset",  "schedule_preset": "daily_9am" }
{ "schedule_kind": "cron",    "cron": "0 9 * * 1-5" }
```

- Presets are validated server-side; unknown preset → HTTP 400.
- Raw cron expressions are validated by `triggers_service.validate_cron`
  before saving.
- `GET /api/triggers/presets` lists available presets,
  `GET /api/triggers/templates` returns ready-made task templates.

---

## HTTP API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/triggers` | List triggers |
| `POST` | `/api/triggers` | Create (201) |
| `PATCH` | `/api/triggers/{id}` | Update / enable / disable |
| `DELETE` | `/api/triggers/{id}` | Delete |
| `GET` | `/api/triggers/{id}/preview` | Preview next runs & resolved payload |
| `POST` | `/api/triggers/{id}/run` | Fire immediately (202 Accepted) |

### Create example

```bash
curl -X POST "$API/api/triggers" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Morning pipeline check",
    "schedule_kind": "preset",
    "schedule_preset": "daily_9am",
    "agent_ids": [3],
    "task_template": "Review open deals in stage {{stage}} and summarise risks.",
    "context_template": {"stage": "qualified"},
    "enabled": true
  }'
```

Validation on create/update:

- `name`, `task_template` non-empty; at least one `agent_ids`.
- All `agent_ids` must belong to the caller (`400` with missing ids otherwise).
- Schedule resolved and validated before persisting.

---

## Execution

The scheduler service picks up due triggers, renders
`task_template` + `context_template`, and calls into the agent runner per
bound agent. Manual `POST /run` bypasses the schedule and returns **202**
— execution is asynchronous.

Results land as regular agent messages, so they show up in Conversations
and in traces ([Self-Forging](SELF_FORGING.md) can then freeze good ones).

---

## UI

Manage under **Automations** in the dashboard sidebar:
create/edit dialogs with preset picker or cron input, agent multi-select,
enable toggle, run-now button.

---

## See also

- [`docs/guides/AGENT_DEVELOPMENT.md`](AGENT_DEVELOPMENT.md) — structuring agents that run autonomously
- [`docs/guides/WEBHOOKS.md`](WEBHOOKS.md) — event-driven (inbound) counterpart to scheduled triggers
