// NOTICE: This file is protected under RCF-PL
# Agent Sandbox

How AladdinAI isolates agent code execution from the backend host using Docker containers.

## Overview

When an agent runs a command or executes Python code, the work happens inside a
**per-agent Docker sandbox** — never on the backend host. Each agent gets a
private container with a persistent `/workspace` volume so files survive restarts.

If Docker is unavailable (local dev without a daemon), execution falls back to
host subprocesses under strict resource limits.

```
Agent (LLM) ──function_call──→ Tool
                                    │
                              ensure_sandbox()
                                    │
                              ┌─────┴──────┐
                              ▼            ▼
                         Docker OK    No Docker
                              │            │
                         docker exec   subprocess
                         in container  on host
                              │            │
                         stdout/stderr  stdout/stderr
                              │            │
                              ▼            ▼
                          mask_secrets()
                              │
                              ▼
                         Return to LLM context
```

## Container lifecycle

### Creation

Containers are created **lazily** on first tool invocation and reused across
subsequent calls. The naming scheme is deterministic:

| Resource | Name pattern | Purpose |
|----------|-------------|---------|
| Container | `aladdin-sbx-u{uid}-a{aid}` | One sandbox per (user, agent) pair |
| Volume | `agent-ws-u{uid}-a{aid}` | Persistent workspace mounted at `/workspace` |

If `agent_id` is `None` (an ad-hoc unsaved agent), the id is bucketed as `0`
so the user gets one stable sandbox rather than leaking a container per call.

### Container configuration

```
Image:         python:3.12-slim
Command:       sleep infinity  (kept alive; exec'd on demand)
Network:       none             (no internet access)
Root FS:       read-only
tmpfs:         /tmp (64 MB)     (writable scratch space)
Volume:        /workspace       (read-write, persists across restarts)
Memory limit:  512 MB
PIDs limit:    128              (anti fork-bomb)
CPU limit:     1.0 CPU
```

### Teardown

When an agent is deleted, its sandbox is torn down:

```python
from app.services import agent_sandbox

await agent_sandbox.teardown(user_id, agent_id, remove_volume=True)
```

This stops and removes the container, and optionally deletes the volume.
Teardown failures are logged but do not block agent deletion.

## API surface

### `ensure_sandbox(user_id, agent_id) → Optional[str]`

Returns a running container id. Creates the container and volume if they do not
exist; restarts the container if it is stopped. Returns `None` when Docker is
unavailable so callers can fall back to host execution.

### `exec_in_sandbox(container_id, command, *, timeout=15.0, workdir="/workspace") → ExecResult`

Runs `bash -lc <command>` inside the container. On timeout, the command is
killed with `pkill -9` inside the container. Returns an `ExecResult` dataclass:

```python
@dataclass
class ExecResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
```

### `write_file(container_id, path, content)`

Writes a text file into the container. Uses `tarfile` + `put_archive` because
the root fs is read-only; files must go into a volume-mounted directory
(usually `/workspace`).

### `export_artifact(db, user_id, container_id, path, *, mime=None) → Optional[dict]`

Copies a file out of the sandbox into media storage. Lets a user download
what an agent produced (`report.xlsx`, `chart.png`, etc.) through the existing
media pipeline. Returns `None` if the file does not exist.

### `teardown(user_id, agent_id, *, remove_volume=False)`

Stops and removes the sandbox container. If `remove_volume=True`, deletes the
persistent workspace volume as well.

## Tools that use the sandbox

### `run_python_code`

1. Writes the script to a temp file via `write_file()`
2. Runs `python <script>` in the sandbox
3. Returns stdout/stderr and exit code
4. On failure, falls back to host subprocess with rlimits

### `execute_terminal_command`

1. Creates a `TerminalApproval` request in the database (status: `pending`)
2. Sends an `on_step` notification to the UI
3. **Polls for a human verdict** (approve/reject) for up to 120 seconds
4. If approved → runs the command in the sandbox
5. If rejected or timed out → returns the corresponding message

The approval gate ensures that potentially dangerous commands (e.g. `rm -rf`,
`sudo`, destructive operations) require explicit human consent.

## Security model

| Layer | What it prevents |
|-------|-----------------|
| **Docker isolation** | Agent code cannot touch the backend filesystem |
| **`network_mode=none`** | Agent cannot make outbound network requests |
| **Read-only root FS** | Agent cannot modify system binaries or libraries |
| **Resource limits** | CPU/RAM/process limits prevent resource exhaustion |
| **Approval gate** | Dangerous terminal commands require human approval |
| **Secret masking** | API keys and tokens are scrubbed from stdout/stderr before returning to the LLM |

### Secret masking

Before any output is returned to the LLM context, `mask_secrets()` scrubs:

- Patterns like `api_key=...`, `secret=...`, `token=...`, `password=...`, `bearer ...`
- JWT tokens (`eyJ...`)
- Any value matching `SECRET_PATTERNS` in `terminal_tools.py`

## Host fallback

When Docker is unavailable, execution degrades to host subprocesses under
strict `set_rlimits()`:

| Resource | Soft limit | Hard limit |
|----------|-----------|------------|
| CPU time | 5 s | 10 s |
| Virtual memory | 256 MB | 512 MB |
| Processes | 16 | 32 |
| File output | 10 MB | 20 MB |

This path is used for local development without Docker and is **not** recommended
for production.

## File structure

```
backend/app/services/agent_sandbox.py    # Sandbox management (create, exec, teardown)
backend/app/tools/terminal_tools.py      # Terminal execution + approval gate
backend/app/tools/python_sandbox.py      # Python code execution tool
backend/app/services/docker_runner.py    # Docker client (shared with terminal providers)
```

## See also

- [Agent Development](AGENT_DEVELOPMENT.md) — agent configuration and tool assignment
- [Tool Development](TOOL_DEVELOPMENT.md) — how to write new tools that use the sandbox
- [Architecture](../../docs/ARCHITECTURE.md) — full system architecture overview
