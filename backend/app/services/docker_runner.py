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
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import yaml

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


def _client():
    """Construct a docker SDK client against the remote daemon.

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

    # If docker_remote_url is empty, fall back to local socket for dev
    base_url = settings.docker_remote_url or "unix:///var/run/docker.sock"

    tls = None
    if settings.docker_remote_url and settings.docker_tls_cert_path and settings.docker_tls_key_path:
        tls = TLSConfig(
            client_cert=(settings.docker_tls_cert_path, settings.docker_tls_key_path),
            ca_cert=settings.docker_tls_ca_path or None,
            verify=bool(settings.docker_tls_ca_path) and settings.docker_tls_verify,
        )
    try:
        return docker.DockerClient(base_url=base_url, tls=tls, timeout=20)
    except Exception as exc:  # docker.errors.DockerException et al.
        raise DockerUnavailable(f"cannot reach docker daemon: {exc}") from exc


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
    auth_mw = f"{router}-auth"
    strip_mw = f"{router}-strip"
    # Strip the trailing slash so the rule matches both `/p/42` and `/p/42/…`.
    rule = f"Host(`{settings.terminal_public_host}`) && PathPrefix(`/p/{provider_id}`)"
    # Backend URL Traefik calls for forward-auth. The backend service is
    # reachable as `backend:8000` on the shared docker network.
    auth_address = f"http://backend:8000/api/terminal/auth"
    labels = {
        "traefik.enable": "true",
        "traefik.docker.network": settings.terminal_traefik_network,
        f"traefik.http.routers.{router}.rule": rule,
        f"traefik.http.routers.{router}.entrypoints": settings.terminal_traefik_entrypoint,
        f"traefik.http.routers.{router}.service": svc,
        f"traefik.http.routers.{router}.priority": str(settings.terminal_traefik_router_priority),
        f"traefik.http.services.{svc}.loadbalancer.server.port": str(internal_port),
        # forward-auth middleware — Traefik calls /api/terminal/auth before
        # every request. authResponseHeaders is critical so Set-Cookie flows
        # back to the iframe after the initial token consumption.
        f"traefik.http.middlewares.{auth_mw}.forwardauth.address": auth_address,
        f"traefik.http.middlewares.{auth_mw}.forwardauth.authResponseHeaders":
            "Set-Cookie,X-Aladdin-User,X-Aladdin-Provider",
        # Path stripping so the container sees a clean `/` for its own UI.
        f"traefik.http.middlewares.{strip_mw}.stripprefix.prefixes": f"/p/{provider_id}",
        # Order matters: auth first (gate), then strip (rewrite).
        f"traefik.http.routers.{router}.middlewares": f"{auth_mw},{strip_mw}",
    }
    if settings.terminal_traefik_entrypoint == "websecure":
        labels[f"traefik.http.routers.{router}.tls"] = "true"
    return labels


# ── public ops (all async) ──────────────────────────────────────────────

async def is_available() -> bool:
    """Lightweight reachability probe — used by /providers/health."""
    try:
        await asyncio.to_thread(lambda: _client().ping())
        return True
    except Exception:
        return False


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
) -> str:
    """Boot a container for this provider and return its container_id.

    Idempotency: if a previous container with the same provider label
    already exists we remove it first — we never run two instances per row.
    """

    def _do() -> str:
        client = _client()

        merged_labels: Dict[str, str] = {}
        merged_labels.update(labels or {})
        merged_labels[LABEL_USER] = str(user_id)
        merged_labels[LABEL_PROVIDER] = str(provider_id)
        merged_labels[LABEL_TYPE] = provider_type
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

        try:
            container = client.containers.run(
                image=image,
                command=command,
                environment=env or None,
                labels=merged_labels,
                network=settings.terminal_traefik_network,
                detach=True,
                restart_policy={"Name": "unless-stopped"},
                # No port publish — Traefik handles ingress.
                healthcheck=_normalize_healthcheck(healthcheck),
                name=f"aladdin-term-u{user_id}-p{provider_id}",
            )
        except Exception as exc:
            raise DockerOperationError(f"start failed for {image}: {exc}") from exc
        return container.id

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


# ── Traefik file-provider config ────────────────────────────────────────
# Traefik no longer uses the Docker API to discover containers (OrbStack
# incompatibility with API v1.24). Instead, the backend writes a YAML
# routing config for each terminal provider into a shared directory that
# Traefik watches with --providers.file.watch=true.


def _traefik_config_path(provider_id: int) -> str:
    return os.path.join(settings.traefik_dynamic_config_dir, f"terminal-p{provider_id}.yaml")


def _write_traefik_config_sync(
    *, provider_id: int, user_id: int, internal_port: int
) -> None:
    """Write a Traefik dynamic YAML routing config for this provider."""
    container_name = f"aladdin-term-u{user_id}-p{provider_id}"
    router = f"aladdin-term-{provider_id}"
    svc = f"aladdin-term-{provider_id}-svc"
    auth_mw = f"{router}-auth"
    strip_mw = f"{router}-strip"
    rule = (
        f"Host(`{settings.terminal_public_host}`) "
        f"&& PathPrefix(`/p/{provider_id}`)"
    )
    auth_address = "http://backend:8000/api/terminal/auth"

    config: Dict[str, Any] = {
        "http": {
            "routers": {
                router: {
                    "rule": rule,
                    "service": svc,
                    "middlewares": [auth_mw, strip_mw],
                    "priority": settings.terminal_traefik_router_priority,
                    "entryPoints": [settings.terminal_traefik_entrypoint],
                }
            },
            "middlewares": {
                auth_mw: {
                    "forwardAuth": {
                        "address": auth_address,
                        "authResponseHeaders": [
                            "X-Aladdin-User",
                            "X-Aladdin-Provider",
                        ],
                        # addAuthCookiesToResponse is the correct Traefik v3
                        # mechanism to forward Set-Cookie from the auth service
                        # to the browser. authResponseHeaders only forwards
                        # headers to the upstream request, not the browser.
                        "addAuthCookiesToResponse": [
                            settings.terminal_session_cookie_name,
                        ],
                    }
                },
                strip_mw: {
                    "stripPrefix": {
                        "prefixes": [f"/p/{provider_id}"]
                    }
                },
            },
            "services": {
                svc: {
                    "loadBalancer": {
                        "servers": [
                            {"url": f"http://{container_name}:{internal_port}"}
                        ]
                    }
                }
            },
        }
    }

    path = _traefik_config_path(provider_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(config, fh, default_flow_style=False, allow_unicode=True)


def _remove_traefik_config_sync(provider_id: int) -> None:
    """Remove the Traefik routing config file for this provider."""
    try:
        os.remove(_traefik_config_path(provider_id))
    except FileNotFoundError:
        pass


async def write_traefik_config(
    *, provider_id: int, user_id: int, internal_port: int
) -> None:
    """Async wrapper — write Traefik file-provider config for a terminal provider."""
    await asyncio.to_thread(
        _write_traefik_config_sync,
        provider_id=provider_id,
        user_id=user_id,
        internal_port=internal_port,
    )


async def remove_traefik_config(provider_id: int) -> None:
    """Async wrapper — remove Traefik file-provider config for a terminal provider."""
    await asyncio.to_thread(_remove_traefik_config_sync, provider_id)
