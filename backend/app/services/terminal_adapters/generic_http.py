# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""
Generic HTTP-behind-Traefik adapter.

Used by every plugin whose contract is "container exposing one HTTP/WS port
on `internal_port`, gated by our edge token". That's ttyd, wetty (after the
adapter wires SSH target from session context — TODO when ssh-proxy lands),
code-server, and most future entries.

The adapter is stateless and pure: it folds the manifest defaults with the
per-row `config` (a small JSON blob in the DB) into a `ContainerSpec`. It
never talks to docker, never touches the DB, never sees the token in the
spec — the token rides in the URL only.
"""

from __future__ import annotations

from typing import Any, Dict

from app.services.terminal_adapters.base import ContainerSpec, TerminalAdapter


class GenericHttpAdapter(TerminalAdapter):
    """Adapter for any plugin that's a single HTTP/WS port behind Traefik."""

    def __init__(self, adapter_label: str = "generic-http") -> None:
        # Goes into the container label set as `aladdin.terminal.adapter`.
        # Helps `docker ps --filter` debugging without DB access.
        self._label = adapter_label

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
        # `command` and `env`. Lists in config replace, dicts merge — same
        # rule across adapters so the UI can render a uniform form.
        command = list(config.get("command") or manifest.get("command") or [])

        env_merged: Dict[str, str] = {}
        env_merged.update(manifest.get("env") or {})
        env_merged.update(config.get("env") or {})
        # Coerce values to strings — docker SDK rejects ints/bools silently
        # on some platforms.
        env_merged = {k: ("" if v is None else str(v)) for k, v in env_merged.items()}

        internal_port = int(manifest.get("internal_port") or 7681)

        return ContainerSpec(
            image=image,
            command=command or None,
            env=env_merged,
            labels={
                "aladdin.terminal.adapter": self._label,
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
