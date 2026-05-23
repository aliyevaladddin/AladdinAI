# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""
Remote Docker daemon adapter.

We talk to a docker daemon that lives on a separate host (the "remote" in
the user's deployment choice) over TLS. That daemon runs:
  * a Traefik container fronting `terminal_public_host`,
  * one container per (user, terminal provider) attached to the shared
    `terminal_traefik_network`, labelled for Traefik routing.

This module is the **only** place that imports `docker`. The router and the
adapters stay pure. Every blocking docker SDK call is wrapped in
`asyncio.to_thread` so it doesn't stall the event loop.

If `settings.docker_remote_url` is empty we treat docker as not configured:
operations raise `DockerUnavailable` and the router maps that to HTTP 503.
The provider can still be installed (a DB row exists) — only start/stop is
disabled, which is the right semantics for dev environments without remote
docker creds yet.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings


class DockerUnavailable(RuntimeError):
    """Raised when the remote docker daemon isn't reachable or configured."""


class DockerOperationError(RuntimeError):
    """Raised when a docker API call returns an error we can't paper over."""


@dataclass(frozen=True)
class ContainerStatus:
    container_id: str
    state: str            # "created" | "running" | "exited" | "dead" | "paused" | …
    health: Optional[str] # "starting" | "healthy" | "unhealthy" | None
    error: Optional[str]


# Label namespace — everything we own lives under aladdin.terminal.* so a
# `docker ps --filter label=aladdin.terminal.user_id=N` is enough to find a
# user's containers without DB access.
LABEL_NS = "aladdin.terminal"
LABEL_USER = f"{LABEL_NS}.user_id"
LABEL_PROVIDER = f"{LABEL_NS}.provider_id"
LABEL_TYPE = f"{LABEL_NS}.type"

# Owner contract — every container we spawn carries `aladdin.owner.kind` +
# `aladdin.owner.id`. Today `kind` is always "user", but the contract is
# designed so /agents can adopt it without a schema migration: an
# AI-agent-launched terminal would set kind="agent" and id=<agent_uuid>,
# and the rest of docker_runner stays unchanged.
LABEL_OWNER_KIND = "aladdin.owner.kind"
LABEL_OWNER_ID = "aladdin.owner.id"

# Session bookkeeping — `session.id` is the long-running provider session
# (one per provider row), `session.ttl` is the wall-clock seconds the
# spawner expected the session to live. We don't enforce TTL inside the
# container — a janitor job uses the label to reap orphans.
LABEL_SESSION_ID = "aladdin.session.id"
LABEL_SESSION_TTL = "aladdin.session.ttl"


# Default resource limits applied to *every* container, regardless of
# owner kind. Numbers tuned for a single web-terminal process; agent
# workloads (future) can pass overrides via `resource_limits=`.
DEFAULT_CPUS = 1.0          # NanoCPUs = cpus * 1e9
DEFAULT_MEM_BYTES = 512 * 1024 * 1024   # 512 MiB
DEFAULT_PIDS_LIMIT = 256
DEFAULT_BLKIO_WEIGHT = 500


def _resolve_base_url() -> str:
    """Pick the docker daemon URL we'll talk to.

    Two paths, in order:
      1. Explicit `docker_remote_url` from .env — `tcp://…` for remote TLS,
         or `unix://…` if the operator deliberately points us at a local
         socket. We never second-guess an explicit value.
      2. Empty config → fall back to the local unix socket at
         `unix:///var/run/docker.sock`. This is the "own machine" dev path:
         the marketplace works without any TLS/remote setup as long as the
         local docker daemon is up and readable by the backend process
         (uid in the `docker` group, or the socket bind-mounted into the
         backend container).
    """
    url = (settings.docker_remote_url or "").strip()
    if url:
        return url
    return "unix:///var/run/docker.sock"


def _client():
    """Construct a docker SDK client against the configured (or local) daemon.

    Lazy-imports `docker` so the rest of the app keeps booting in environments
    that didn't install the dep yet (the requirements pin is new in this
    commit and existing deployments need `pip install -r requirements.txt`).
    """
    try:
        import docker
        from docker.tls import TLSConfig
    except ImportError as exc:
        raise DockerUnavailable(
            "docker SDK not installed — run `pip install -r requirements.txt`",
        ) from exc

    base_url = _resolve_base_url()
    # TLS only applies to `tcp://` transports. A unix socket can't be TLS-wrapped;
    # silently ignoring stray cert paths keeps a partially-filled .env from
    # blowing up the local dev path.
    tls = None
    if base_url.startswith("tcp://") and settings.docker_tls_cert_path and settings.docker_tls_key_path:
        tls = TLSConfig(
            client_cert=(settings.docker_tls_cert_path, settings.docker_tls_key_path),
            ca_cert=settings.docker_tls_ca_path or None,
            verify=bool(settings.docker_tls_ca_path) and settings.docker_tls_verify,
        )
    try:
        return docker.DockerClient(base_url=base_url, tls=tls, timeout=20)
    except Exception as exc:  # docker.errors.DockerException et al.
        raise DockerUnavailable(f"cannot reach docker daemon ({base_url}): {exc}") from exc


# ── duration parsing ────────────────────────────────────────────────────
# YAML carries human-friendly durations like "30s"; docker SDK wants
# nanoseconds. We accept a tiny grammar: integer + (ns|us|ms|s|m|h).

_DUR_RE = re.compile(r"^\s*(\d+)\s*(ns|us|ms|s|m|h)?\s*$")
_DUR_MUL = {None: 1_000_000_000, "ns": 1, "us": 1_000, "ms": 1_000_000,
            "s": 1_000_000_000, "m": 60_000_000_000, "h": 3_600_000_000_000}


def _duration_to_ns(value: Any) -> int:
    if isinstance(value, int):
        return value
    if value is None:
        return 0
    m = _DUR_RE.match(str(value))
    if not m:
        raise ValueError(f"unrecognised duration: {value!r}")
    n, unit = int(m.group(1)), m.group(2)
    return n * _DUR_MUL[unit]


def _normalize_healthcheck(hc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not hc:
        return None
    out: Dict[str, Any] = {"test": list(hc["test"])}
    for k in ("interval", "timeout", "start_period"):
        if k in hc and hc[k] is not None:
            out[k] = _duration_to_ns(hc[k])
    if "retries" in hc and hc["retries"] is not None:
        out["retries"] = int(hc["retries"])
    return out


# ── Traefik labels ──────────────────────────────────────────────────────
# All routing is done by labels on the container. The Traefik instance is
# configured (outside this codebase) with the docker provider pointed at
# this network and `exposedByDefault=false`, so unlabelled containers are
# ignored.

def _traefik_labels(*, provider_id: int, internal_port: int) -> Dict[str, str]:
    router = f"aladdin-term-{provider_id}"
    svc = f"aladdin-term-{provider_id}-svc"
    # Strip the trailing slash so the rule matches both `/p/42` and `/p/42/…`.
    rule = f"Host(`{settings.terminal_public_host}`) && PathPrefix(`/p/{provider_id}`)"
    labels = {
        "traefik.enable": "true",
        "traefik.docker.network": settings.terminal_traefik_network,
        f"traefik.http.routers.{router}.rule": rule,
        f"traefik.http.routers.{router}.entrypoints": settings.terminal_traefik_entrypoint,
        f"traefik.http.routers.{router}.service": svc,
        f"traefik.http.routers.{router}.priority": str(settings.terminal_traefik_router_priority),
        f"traefik.http.services.{svc}.loadbalancer.server.port": str(internal_port),
        # Path stripping so the container sees a clean `/` for its own UI.
        # The named middleware is per-router to avoid collisions.
        f"traefik.http.middlewares.{router}-strip.stripprefix.prefixes": f"/p/{provider_id}",
        f"traefik.http.routers.{router}.middlewares": f"{router}-strip",
    }
    if settings.terminal_traefik_entrypoint == "websecure":
        labels[f"traefik.http.routers.{router}.tls"] = "true"
    return labels


# ── public ops (all async) ──────────────────────────────────────────────

def _ensure_network(client) -> None:
    """Create the Traefik network if it doesn't exist yet.

    In production the operator pre-creates `aladdin_terminal` so Traefik
    is already attached to it. In a local-dev `unix://` setup nothing has
    created it for us — so we make it ourselves, idempotently. We never
    delete it: a stray empty network is cheap.
    """
    name = settings.terminal_traefik_network
    try:
        existing = client.networks.list(names=[name])
        if existing:
            return
        client.networks.create(name, driver="bridge", check_duplicate=True)
    except Exception:
        # If create races with another caller or the daemon refuses, fall
        # through — `containers.run(network=…)` will surface a clearer error.
        pass


async def is_available() -> bool:
    """Lightweight reachability probe — used by /providers/health."""
    try:
        await asyncio.to_thread(lambda: _client().ping())
        return True
    except Exception:
        return False


# ── runtime diagnostics ────────────────────────────────────────────────
# These helpers exist so that when a `start_provider` call dies with a
# generic "cannot reach docker daemon" we can tell the operator *why* in
# plain English (e.g. "you're inside a devcontainer without the docker
# socket mounted"). The /providers/health endpoint exposes the same data
# so the UI can preflight-check before offering Start.

@dataclass(frozen=True)
class RuntimeDiagnostics:
    docker_sdk_installed: bool
    docker_socket_path: Optional[str]
    docker_socket_exists: bool
    docker_daemon_reachable: bool
    running_in_container: bool
    host_bind_iframe_reachable: bool
    daemon_version: Optional[str]
    base_url: str
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _detect_running_in_container() -> bool:
    """True if this process is itself running inside a container.

    Two cheap signals, OR'd together so we don't miss either runtime:
      * `/.dockerenv` — docker writes this marker file on every container
        it boots, even when the cgroup hierarchy is hidden.
      * `/proc/1/cgroup` — first pid's cgroup line mentions `docker`,
        `containerd`, `kubepods`, or `libpod` (podman) when containerized.
    Best-effort: any read error means "not detected", we don't raise.
    """
    try:
        if Path("/.dockerenv").exists():
            return True
    except OSError:
        pass
    try:
        cgroup = Path("/proc/1/cgroup").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    needles = ("docker", "containerd", "kubepods", "libpod")
    return any(n in cgroup for n in needles)


def _extract_socket_path(base_url: str) -> Optional[str]:
    """Pull the filesystem path out of a `unix://` URL; None for tcp."""
    if not base_url.startswith("unix://"):
        return None
    return base_url[len("unix://"):]


def _socket_exists(path: Optional[str]) -> bool:
    if not path:
        return False
    try:
        return Path(path).exists()
    except OSError:
        return False


def _build_recommendations(
    *,
    sdk_installed: bool,
    in_container: bool,
    socket_path: Optional[str],
    socket_exists: bool,
    daemon_reachable: bool,
    bind_host: str,
) -> List[str]:
    """Translate the raw probe results into operator-facing guidance.

    Order matters — the first item is what `start_provider` will surface
    in the HTTP 503 `detail`, so the most likely root cause goes first.
    """
    out: List[str] = []
    if not sdk_installed:
        out.append(
            "Install the python docker SDK: `pip install docker==7.1.0` "
            "in the backend venv, then restart uvicorn."
        )
        # If the SDK isn't even importable everything below is moot.
        return out

    if in_container and not socket_exists:
        out.append(
            "Backend is running inside a container without "
            f"`{socket_path or '/var/run/docker.sock'}` mounted. Rebuild "
            "your devcontainer with the docker-outside-of-docker feature, "
            "or add a bind-mount of the host docker socket to the backend "
            "service in docker-compose.yml."
        )
    elif not socket_exists and (socket_path or "").startswith("/"):
        out.append(
            f"Docker unix socket not found at `{socket_path}`. Confirm the "
            "docker daemon is installed and running on this host, or point "
            "DOCKER_REMOTE_URL at a reachable tcp:// daemon."
        )

    if socket_exists and not daemon_reachable:
        out.append(
            "Docker socket is present but the daemon is not responding — "
            "check that the docker engine is running on the host and that "
            "the backend user has permission to read the socket."
        )

    if in_container and bind_host == "127.0.0.1":
        out.append(
            "Backend is containerized but spawned terminals are bound to "
            "127.0.0.1 (loopback inside the container, unreachable from the "
            "host browser). Set TERMINAL_LOCAL_BIND_HOST=0.0.0.0 in the "
            "backend environment so the published ports are visible to the "
            "iframe."
        )

    return out


def _diagnose_sync() -> RuntimeDiagnostics:
    """Blocking diagnostics — call via `asyncio.to_thread`.

    Wraps every probe in try/except so a partially-broken environment
    still produces a useful report instead of bubbling an exception.
    """
    base_url = _resolve_base_url()
    socket_path = _extract_socket_path(base_url)
    socket_exists = _socket_exists(socket_path)
    in_container = _detect_running_in_container()
    bind_host = (settings.terminal_local_bind_host or "").strip()

    sdk_installed = False
    daemon_reachable = False
    daemon_version: Optional[str] = None
    try:
        import docker  # noqa: F401  (presence check)
        sdk_installed = True
    except ImportError:
        sdk_installed = False

    if sdk_installed:
        try:
            client = _client()
            client.ping()
            daemon_reachable = True
            try:
                ver = client.version() or {}
                daemon_version = str(ver.get("Version") or "") or None
            except Exception:
                daemon_version = None
        except Exception:
            daemon_reachable = False

    # An iframe pointed at `http://localhost:<host_port>` can only reach
    # the spawned container if the published port is bound to a host-
    # visible interface. Inside a container, 127.0.0.1 is the *container's*
    # loopback, not the host's — so the iframe gets ECONNREFUSED.
    host_bind_iframe_reachable = not (in_container and bind_host == "127.0.0.1")

    recommendations = _build_recommendations(
        sdk_installed=sdk_installed,
        in_container=in_container,
        socket_path=socket_path,
        socket_exists=socket_exists,
        daemon_reachable=daemon_reachable,
        bind_host=bind_host,
    )

    return RuntimeDiagnostics(
        docker_sdk_installed=sdk_installed,
        docker_socket_path=socket_path,
        docker_socket_exists=socket_exists,
        docker_daemon_reachable=daemon_reachable,
        running_in_container=in_container,
        host_bind_iframe_reachable=host_bind_iframe_reachable,
        daemon_version=daemon_version,
        base_url=base_url,
        recommendations=recommendations,
    )


async def diagnose_runtime() -> RuntimeDiagnostics:
    """Async wrapper so callers can `await` from FastAPI handlers."""
    return await asyncio.to_thread(_diagnose_sync)


async def pull_image(image: str) -> None:
    def _do():
        client = _client()
        try:
            client.images.pull(image)
        except Exception as exc:
            raise DockerOperationError(f"pull failed for {image}: {exc}") from exc
    await asyncio.to_thread(_do)


async def start_container(
    *,
    provider_id: int,
    user_id: int,
    provider_type: str,
    image: str,
    command: Optional[List[str]],
    env: Dict[str, str],
    labels: Dict[str, str],
    healthcheck: Optional[Dict[str, Any]],
    internal_port: int,
    owner_kind: str = "user",
    owner_id: Optional[str] = None,
    session_id: Optional[str] = None,
    session_ttl_seconds: Optional[int] = None,
    resource_limits: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Optional[int]]:
    """Boot a container for this provider and return (container_id, host_port).

    Two layouts, picked by `settings.terminal_local_publish`:

    * **Traefik mode** (default for production): container joins the shared
      `terminal_traefik_network`, no host port published, Traefik routes
      `/p/{id}` to it via labels. `host_port` is None.
    * **Local-publish mode** (dev / own-machine path): container's
      `internal_port` is published on a random host port bound to
      `terminal_local_bind_host` (127.0.0.1 by default). No Traefik
      involvement, no shared network. `host_port` is returned so the
      router can store it on the provider row and the adapter can build a
      `http://localhost:<host_port>/` URL.

    Idempotency: if a previous container with the same provider label
    already exists we remove it first — we never run two instances per row.
    """

    def _do() -> Tuple[str, Optional[int]]:
        client = _client()
        local_mode = bool(settings.terminal_local_publish)

        merged_labels: Dict[str, str] = {}
        merged_labels.update(labels or {})
        merged_labels[LABEL_USER] = str(user_id)
        merged_labels[LABEL_PROVIDER] = str(provider_id)
        merged_labels[LABEL_TYPE] = provider_type
        # Owner contract — same shape for users and (future) agents.
        merged_labels[LABEL_OWNER_KIND] = owner_kind
        merged_labels[LABEL_OWNER_ID] = str(owner_id if owner_id is not None else user_id)
        # Session bookkeeping for the orphan-reaper job.
        if session_id is not None:
            merged_labels[LABEL_SESSION_ID] = str(session_id)
        if session_ttl_seconds is not None:
            merged_labels[LABEL_SESSION_TTL] = str(int(session_ttl_seconds))
        if not local_mode:
            # Traefik routing labels only make sense when Traefik is the
            # one reading them. In local-publish mode they'd just be noise.
            merged_labels.update(_traefik_labels(
                provider_id=provider_id,
                internal_port=internal_port,
            ))

        # Reap any stale container with our provider label.
        for old in client.containers.list(
            all=True,
            filters={"label": f"{LABEL_PROVIDER}={provider_id}"},
        ):
            try:
                old.remove(force=True)
            except Exception:
                # Already gone or daemon racing; either is fine.
                pass

        # Resource limits — cgroup-level isolation applied to every
        # container, regardless of kind. Caller can override individual
        # knobs via `resource_limits={"cpus": 2, "mem_bytes": …}`. Same
        # contract will accept agent workloads later (they'll just pass
        # tighter numbers).
        rl = dict(resource_limits or {})
        cpus = float(rl.get("cpus", DEFAULT_CPUS))
        mem_bytes = int(rl.get("mem_bytes", DEFAULT_MEM_BYTES))
        pids_limit = int(rl.get("pids_limit", DEFAULT_PIDS_LIMIT))
        blkio_weight = int(rl.get("blkio_weight", DEFAULT_BLKIO_WEIGHT))

        run_kwargs: Dict[str, Any] = dict(
            image=image,
            command=command,
            environment=env or None,
            labels=merged_labels,
            detach=True,
            restart_policy={"Name": "unless-stopped"},
            healthcheck=_normalize_healthcheck(healthcheck),
            name=f"aladdin-term-u{user_id}-p{provider_id}",
            # cgroup limits — keep one runaway terminal from starving the
            # host. `nano_cpus` is the docker-SDK name for CPU quota.
            nano_cpus=int(cpus * 1_000_000_000),
            mem_limit=mem_bytes,
            pids_limit=pids_limit,
            blkio_weight=blkio_weight,
        )
        if local_mode:
            # `("host", None)` tells the docker daemon to pick a free port.
            # We resolve the actual port by reloading the container after run
            # — `containers.run` returns before NetworkSettings are populated.
            run_kwargs["ports"] = {
                f"{internal_port}/tcp": (settings.terminal_local_bind_host, None),
            }
        else:
            _ensure_network(client)
            run_kwargs["network"] = settings.terminal_traefik_network

        try:
            container = client.containers.run(**run_kwargs)
        except Exception as exc:
            raise DockerOperationError(f"start failed for {image}: {exc}") from exc

        host_port: Optional[int] = None
        if local_mode:
            try:
                container.reload()
                bindings = (
                    (container.attrs.get("NetworkSettings") or {}).get("Ports") or {}
                ).get(f"{internal_port}/tcp") or []
                # docker returns a list of host-binding dicts; in practice we
                # only ever ask for one. Pick the first non-empty HostPort.
                for b in bindings:
                    hp = (b or {}).get("HostPort")
                    if hp:
                        host_port = int(hp)
                        break
            except Exception:
                # Container is up; we just couldn't read back the port.
                # Caller will surface this as last_error on the row.
                host_port = None
        return container.id, host_port

    return await asyncio.to_thread(_do)


async def stop_container(container_id: str) -> None:
    def _do():
        try:
            c = _client().containers.get(container_id)
        except Exception:
            return  # Already gone — treat as stopped.
        try:
            c.stop(timeout=10)
        except Exception as exc:
            raise DockerOperationError(f"stop failed for {container_id}: {exc}") from exc
    await asyncio.to_thread(_do)


async def remove_container(container_id: str) -> None:
    def _do():
        try:
            c = _client().containers.get(container_id)
        except Exception:
            return
        try:
            c.remove(force=True)
        except Exception as exc:
            raise DockerOperationError(f"remove failed for {container_id}: {exc}") from exc
    await asyncio.to_thread(_do)


async def inspect_status(container_id: str) -> ContainerStatus:
    def _do() -> ContainerStatus:
        try:
            c = _client().containers.get(container_id)
        except Exception as exc:
            return ContainerStatus(container_id=container_id, state="missing", health=None,
                                   error=str(exc))
        state = c.attrs.get("State", {}) or {}
        return ContainerStatus(
            container_id=container_id,
            state=state.get("Status", "unknown"),
            health=(state.get("Health") or {}).get("Status"),
            error=state.get("Error") or None,
        )
    return await asyncio.to_thread(_do)


async def container_logs(container_id: str, *, tail: int = 200) -> str:
    """Fetch the last `tail` lines of combined stdout/stderr from a container.

    Returns a decoded string (UTF-8 with replacement). We don't try to split
    streams — the UI shows them as one log feed, which matches what `docker
    logs` itself produces by default. If the container is gone or the daemon
    is unreachable we surface a one-line error instead of raising — the
    endpoint upstream of us treats this as a soft failure.
    """
    def _do() -> str:
        try:
            c = _client().containers.get(container_id)
        except DockerUnavailable as exc:
            return f"[docker unavailable: {exc}]"
        except Exception as exc:
            return f"[container not found: {exc}]"
        try:
            raw = c.logs(stdout=True, stderr=True, tail=int(tail), timestamps=False)
        except Exception as exc:
            return f"[logs unavailable: {exc}]"
        if isinstance(raw, bytes):
            return raw.decode("utf-8", errors="replace")
        return str(raw)
    return await asyncio.to_thread(_do)


async def list_containers_by_user(user_id: int) -> List[Dict[str, Any]]:
    """Lightweight listing — used by GET /providers for status hydration."""
    def _do() -> List[Dict[str, Any]]:
        client = _client()
        out: List[Dict[str, Any]] = []
        for c in client.containers.list(all=True, filters={"label": f"{LABEL_USER}={user_id}"}):
            labels = c.labels or {}
            state = c.attrs.get("State", {}) or {}
            out.append({
                "container_id": c.id,
                "provider_id": int(labels.get(LABEL_PROVIDER, 0)) or None,
                "state": state.get("Status", "unknown"),
                "health": (state.get("Health") or {}).get("Status"),
            })
        return out
    return await asyncio.to_thread(_do)
