# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""
Adapter protocol shared by every terminal provider (ttyd, wetty, guacamole, …).

An adapter translates a `TerminalProvider` row + a per-user request into:
  (a) a container spec that docker_runner can boot, and
  (b) a session URL the frontend iframe can navigate to.

Adapters never call docker themselves and never read the DB — they are pure
functions over (provider, user, token). This keeps them trivially testable
and lets docker_runner stay the only place that talks to the daemon.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol


@dataclass
class ContainerSpec:
    """What docker_runner needs to start a container for a provider."""

    image: str
    command: Optional[List[str]] = None
    env: Dict[str, str] = field(default_factory=dict)
    # Volume mounts: list of "host_path:container_path" or "host_path:container_path:ro"
    volumes: List[str] = field(default_factory=list)
    # Container label map — docker_runner merges in its own bookkeeping
    # labels (aladdin.terminal.user_id, aladdin.terminal.provider_id) and
    # the Traefik routing labels on top of this.
    labels: Dict[str, str] = field(default_factory=dict)
    # Healthcheck spec mirrors docker SDK shape: {"test": [...], "interval":
    # nanoseconds, "timeout": nanoseconds, "retries": int, "start_period":
    # nanoseconds}. docker_runner does the unit conversion from the YAML
    # string form ("30s") to nanoseconds.
    healthcheck: Optional[Dict[str, Any]] = None
    # Internal port the process listens on inside the container — used both
    # by Traefik (loadbalancer.server.port) and by future direct-port
    # implementations.
    internal_port: int = 7681


class TerminalAdapter(Protocol):
    """Adapter contract.

    Implementations are stateless. They read manifest+row data and return
    transport-only descriptions. The router decides when to call them.
    """

    def build_container_spec(
        self,
        *,
        provider_id: int,
        user_id: int,
        image: str,
        manifest: Dict[str, Any],
        config: Dict[str, Any],
    ) -> ContainerSpec:
        """Produce a ContainerSpec from manifest + per-row config overrides."""
        ...

    def build_session_url(
        self,
        *,
        provider_id: int,
        url_template: str,
        scheme: str,
        host: str,
        token: str,
    ) -> str:
        """Substitute {provider_id}, {token}, {scheme}, {host} into the template."""
        ...
