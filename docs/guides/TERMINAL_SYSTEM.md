// NOTICE: This file is protected under RCF-PL
# Modular Terminal System

AladdinAI ships a pluggable terminal system: instead of one hardcoded
web-terminal, users install **terminal providers** from a marketplace and
run them as isolated containers.

---

## Concepts

| Concept | What it is |
|---|---|
| **Manifest** | Declarative description of a provider: image, internal port, URL template, whether it needs an SSH proxy |
| **TerminalProvider** | A user's installed instance of a manifest (stored in Postgres, config encrypted at rest) |
| **Session** | A running container + short-lived access token issued by the token broker |
| **SSH proxy** | Optional component for providers that target remote VMs (`requires_ssh_proxy: true`) |

---

## Marketplace

`GET /api/terminal/marketplace` returns the builtin manifests the backend
can install. Each entry:

```json
{
  "type": "ttyd",
  "name": "ttyd",
  "description": "Lightweight web terminal",
  "image": "ghcr.io/.../ttyd:latest",
  "internal_port": 7681,
  "requires_ssh_proxy": false
}
```

Manifests are loaded from YAML at startup (`terminal_manifest.py`) — adding
a new provider is a file drop, no code change.

---

## Lifecycle

```
install → start → (session) → stop → uninstall
```

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/terminal/providers` | Install a provider (`type`, optional `name`, `config`, `vm_id`) |
| `GET` | `/api/terminal/providers` | List installed providers |
| `DELETE` | `/api/terminal/providers/{id}` | Uninstall |
| `POST` | `/api/terminal/providers/{id}/start` | Pull image, create container, mark `running` |
| `POST` | `/api/terminal/providers/{id}/stop` | Stop container |
| `POST` | `/api/terminal/providers/{id}/set_active` | Mark as the active provider |
| `GET` | `/api/terminal/providers/{id}/logs` | Container logs |
| `POST` | `/api/terminal/session` | Create a session → returns URL + token cookie |
| `DELETE` | `/api/terminal/session/{sid}` | Terminate session |

Sessions are brokered by `terminal_token_broker.py`: tokens are short-lived,
delivered via HttpOnly cookie, and verified per request. The frontend never
sees long-lived credentials.

---

## Security

- Provider `config` blobs are **encrypted with Fernet** before storage and
  decrypted only in-process (`app.crypto.decrypt`). Parsing uses `_safe_json`
  — malformed config can never crash a request.
- Containers run through `docker_runner` with no host mounts of secrets;
  agent-facing execution is additionally sandboxed (see
  [Agent Sandbox](AGENT_SANDBOX.md)).
- SSH proxy providers verify hosts with **TOFU known-hosts pinning**
  (`ssh_known_hosts.py`) to prevent MITM on first connect.
- All routes require authentication; every provider row is scoped by
  `user_id`.

---

## UI

Manage providers under **Settings → Terminal**
(`frontend/src/app/(dashboard)/dashboard/settings/terminal/page.tsx`):
marketplace grid, install dialog, start/stop controls, live logs.

Approval-gated commands executed *inside* terminals are handled separately —
see [`backend/app/routers/terminal_approval.py`](../../backend/app/routers/terminal_approval.py).

---

## See also

- [`docs/guides/AGENT_SANDBOX.md`](AGENT_SANDBOX.md) — how agent code execution is isolated
- [`docs/adr/0011-multi-agent-swarm-and-tools.md`](../adr/0011-multi-agent-swarm-and-tools.md)
