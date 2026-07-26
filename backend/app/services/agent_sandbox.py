# NOTICE: This file is protected under RCF-PL
"""Per-agent execution sandbox.

Each agent gets its own long-lived Docker container with a private named volume
mounted at ``/workspace``. Terminal commands and Python code run *inside* that
container via ``docker exec`` — never on the backend host — so an agent can
create, read and mutate files without ever touching the backend filesystem.

Why not ``docker_runner.start_container``: that path is specialised for the
terminal *providers* (Traefik labels, restart policy, provider_id). Sandboxes
are simpler and different, so we talk to the same lazily-imported client
(:func:`docker_runner._client`) directly.

Isolation choices:
  - Private named volume ``agent-ws-<uid>-<aid>`` → ``/workspace`` (files survive
    a container restart, are isolated from the host, and finished artifacts can
    be exported to media storage via :func:`export_artifact`).
  - ``network_mode="none"`` by default — the sandbox cannot reach the network.
  - Hard limits: memory, pids (anti fork-bomb), read-only root except the
    workspace volume and a small tmpfs.

Everything degrades gracefully: if Docker is unavailable
(:func:`is_available` is False) callers fall back to host execution.
"""

from __future__ import annotations

import asyncio
import logging
import shlex
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import docker_runner
from app.services.docker_runner import DockerUnavailable

log = logging.getLogger(__name__)

WORKDIR = "/workspace"
SANDBOX_IMAGE = "python:3.12-slim"
_LABEL_SANDBOX = "aladdinai.sandbox"

# Resource ceilings applied to every sandbox container.
_MEM_LIMIT = "512m"
_PIDS_LIMIT = 128
_NANO_CPUS = 1_000_000_000  # 1.0 CPU


@dataclass
class ExecResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


def _names(user_id: int, agent_id: int | None) -> tuple[str, str]:
    """Container and volume names for a (user, agent) pair.

    agent_id may be None (an ad-hoc/unsaved agent); bucket those under 0 so the
    user still gets one stable sandbox rather than leaking a container per call.
    """
    aid = agent_id if agent_id is not None else 0
    return f"aladdin-sbx-u{user_id}-a{aid}", f"agent-ws-u{user_id}-a{aid}"


# [RCF:PROTECTED]
async def is_available() -> bool:
    """True if the Docker daemon is reachable (mirrors docker_runner)."""
    return await docker_runner.is_available()


# [RCF:PROTECTED]
async def ensure_sandbox(user_id: int, agent_id: int | None) -> Optional[str]:
    """Return a running sandbox container id for this agent, creating it if needed.

    Returns None when Docker is unavailable so the caller can fall back to host
    execution.
    """
    container_name, volume_name = _names(user_id, agent_id)

    def _do() -> Optional[str]:
        client = docker_runner._client()

        # Reuse an existing sandbox if it's still around; restart if stopped.
        try:
            existing = client.containers.get(container_name)
            if existing.status != "running":
                existing.start()
            return existing.id
        except Exception:
            pass  # Not found — create below.

        # Idempotent volume (docker no-ops if it already exists).
        try:
            client.volumes.create(name=volume_name, labels={_LABEL_SANDBOX: str(user_id)})
        except Exception:
            pass

        container = client.containers.run(
            image=SANDBOX_IMAGE,
            # Keep the container alive; we exec into it on demand.
            command=["sleep", "infinity"],
            name=container_name,
            labels={_LABEL_SANDBOX: str(user_id)},
            detach=True,
            network_mode="none",
            working_dir=WORKDIR,
            volumes={volume_name: {"bind": WORKDIR, "mode": "rw"}},
            mem_limit=_MEM_LIMIT,
            pids_limit=_PIDS_LIMIT,
            nano_cpus=_NANO_CPUS,
            read_only=True,               # root fs read-only …
            tmpfs={"/tmp": "size=64m"},   # … except a small scratch /tmp
            # /workspace stays writable because it's a volume mount.
        )
        return container.id

    try:
        return await asyncio.to_thread(_do)
    except DockerUnavailable as exc:
        log.info("agent_sandbox: docker unavailable, host fallback: %s", exc)
        return None
    except Exception as exc:
        log.warning("agent_sandbox: ensure failed, host fallback: %s", exc)
        return None


# [RCF:PROTECTED]
async def exec_in_sandbox(
    container_id: str,
    command: str,
    *,
    timeout: float = 15.0,
    workdir: str = WORKDIR,
) -> ExecResult:
    """Run ``bash -lc <command>`` inside the sandbox, capturing output.

    The timeout is enforced host-side: on expiry the exec'd process tree is
    killed inside the container so a hung command cannot pin a slot forever.
    """

    def _do() -> ExecResult:
        client = docker_runner._client()
        container = client.containers.get(container_id)
        # exec_run with demux to separate stdout/stderr.
        exec_id = client.api.exec_create(
            container.id,
            cmd=["bash", "-lc", command],
            workdir=workdir,
            stdout=True,
            stderr=True,
        )["Id"]
        out = client.api.exec_start(exec_id, demux=True)
        stdout_b, stderr_b = out if isinstance(out, tuple) else (out, None)
        info = client.api.exec_inspect(exec_id)
        return ExecResult(
            exit_code=info.get("ExitCode") if info.get("ExitCode") is not None else -1,
            stdout=(stdout_b or b"").decode("utf-8", "replace"),
            stderr=(stderr_b or b"").decode("utf-8", "replace"),
        )

    def _kill(pattern: str) -> None:
        try:
            client = docker_runner._client()
            client.containers.get(container_id).exec_run(
                ["pkill", "-9", "-f", pattern]
            )
        except Exception:
            pass

    try:
        return await asyncio.wait_for(asyncio.to_thread(_do), timeout=timeout)
    except asyncio.TimeoutError:
        # Best-effort kill of the runaway command inside the container.
        await asyncio.to_thread(_kill, command[:60])
        return ExecResult(
            exit_code=124,
            stdout="",
            stderr=f"Execution timed out after {timeout:.0f}s.",
            timed_out=True,
        )


# [RCF:PROTECTED]
async def write_file(container_id: str, path: str, content: str) -> None:
    """Write a text file into the sandbox workspace (used to stage code)."""

    def _do() -> None:
        import io
        import tarfile

        client = docker_runner._client()
        container = client.containers.get(container_id)
        data = content.encode("utf-8")
        # Extract into the file's directory (a writable volume such as
        # /workspace) with a basename-only entry — the container root fs is
        # read-only, so put_archive("/", ...) would fail there.
        dest_dir = path.rsplit("/", 1)[0] or "/"
        filename = path.rsplit("/", 1)[-1]
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as tar:
            info = tarfile.TarInfo(name=filename)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        stream.seek(0)
        container.put_archive(dest_dir, stream.getvalue())

    await asyncio.to_thread(_do)


# [RCF:PROTECTED]
async def export_artifact(
    db: AsyncSession,
    user_id: int,
    container_id: str,
    path: str,
    *,
    mime: str | None = None,
) -> Optional[dict]:
    """Copy a file out of the sandbox into media storage; return its handle.

    Lets a user download what an agent produced (report.xlsx, chart.png, …)
    through the existing media pipeline. Returns None if the file is absent.
    """

    def _read() -> Optional[bytes]:
        import io
        import tarfile

        client = docker_runner._client()
        container = client.containers.get(container_id)
        try:
            bits, _ = container.get_archive(path)
        except Exception:
            return None
        raw = b"".join(bits)
        with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
            member = next((m for m in tar.getmembers() if m.isfile()), None)
            if member is None:
                return None
            f = tar.extractfile(member)
            return f.read() if f else None

    data = await asyncio.to_thread(_read)
    if data is None:
        return None

    from app.services import media_storage

    filename = path.rsplit("/", 1)[-1]
    return await media_storage.save_bytes(
        db, user_id, data, mime, original_filename=filename
    )


# [RCF:PROTECTED]
async def teardown(user_id: int, agent_id: int | None, *, remove_volume: bool = False) -> None:
    """Stop and remove the sandbox container (optionally its volume too)."""
    container_name, volume_name = _names(user_id, agent_id)

    def _do() -> None:
        client = docker_runner._client()
        try:
            client.containers.get(container_name).remove(force=True)
        except Exception:
            pass
        if remove_volume:
            try:
                client.volumes.get(volume_name).remove(force=True)
            except Exception:
                pass

    try:
        await asyncio.to_thread(_do)
    except Exception as exc:
        log.debug("agent_sandbox teardown noop: %s", exc)


# Re-export for callers that build shell commands.
quote = shlex.quote
