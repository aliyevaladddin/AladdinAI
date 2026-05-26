# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""
ttyd adapter — local-shell terminal in a container.

Notes:
  * ttyd has no native auth in this image; the gate is the one-time token in
    the query string, verified by Traefik forward-auth (configured at the
    Traefik layer, out of scope for the adapter).
  * We do NOT pass the token into the container — it's verified by the
    edge, not the workload — so the spec only carries provider env, not
    session secrets.
"""

from __future__ import annotations

from typing import Any, Dict

from app.services.terminal_adapters.base import ContainerSpec, TerminalAdapter
from app.services.terminal_adapters.registry import terminal_adapter


@terminal_adapter("ttyd")
class TtydAdapter(TerminalAdapter):
    def build_container_spec(
        self,
        *,
        provider_id: int,
        user_id: int,
        image: str,
        manifest: Dict[str, Any],
        config: Dict[str, Any],
    ) -> ContainerSpec:
        # Manifest defaults; per-row `config` (JSON in the DB) can override
        # `command` and `env` for advanced users.
        command = list(config.get("command") or manifest.get("command") or [])
        env_merged: Dict[str, str] = {}
        env_merged.update(manifest.get("env") or {})
        env_merged.update(config.get("env") or {})

        internal_port = int(manifest.get("internal_port") or 7681)

        return ContainerSpec(
            image=image,
            command=command or None,
            env=env_merged,
            labels={
                # Adapter-level labels — docker_runner adds its own
                # bookkeeping + Traefik routing on top.
                "aladdin.terminal.adapter": "ttyd",
            },
            healthcheck=manifest.get("healthcheck"),
            internal_port=internal_port,
        )

    def build_session_url(
        self,
        *,
        provider_id: int,
        url_template: str,
        scheme: str,
        host: str,
        token: str,
    ) -> str:
        return url_template.format(
            provider_id=provider_id,
            scheme=scheme,
            host=host,
            token=token,
        )
