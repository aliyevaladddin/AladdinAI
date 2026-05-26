# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""
Wetty adapter — SSH-in-browser terminal.

Unlike ttyd (shell inside container), wetty acts as an SSH client and requires
VM coordinates at container-start time. This adapter reads the user's selected
VM from the provider's config and injects --ssh-host/--ssh-port/--ssh-user into
the wetty command.

The VM selection happens at install time: when the user installs a wetty
provider, they pick which VM it should connect to. The `config` JSON blob in
the DB row carries `{"vm_id": 42}`. If the user wants to SSH into multiple VMs,
they install multiple wetty providers with different names ("AWS prod", "Azure
dev", etc.).
"""

from __future__ import annotations

from typing import Any, Dict

from app.services.terminal_adapters.base import ContainerSpec, TerminalAdapter
from app.services.terminal_adapters.registry import terminal_adapter


@terminal_adapter("wetty")
class WettyAdapter(TerminalAdapter):
    """Adapter for wetty — injects SSH parameters from the user's selected VM."""

    def build_container_spec(
        self,
        *,
        provider_id: int,
        user_id: int,
        image: str,
        manifest: Dict[str, Any],
        config: Dict[str, Any],
    ) -> ContainerSpec:
        # Base command from manifest (node . --port 3000 --base /p/{provider_id}/)
        command = list(manifest.get("command") or [])
        # Interpolate {provider_id} in command arguments
        command = [c.replace("{provider_id}", str(provider_id)) for c in command]

        # Inject SSH parameters if present in config (populated by router from VM)
        if config.get("ssh_host"):
            command.extend(["--ssh-host", config["ssh_host"]])
        if config.get("ssh_port"):
            command.extend(["--ssh-port", str(config["ssh_port"])])
        if config.get("ssh_user"):
            command.extend(["--ssh-user", config["ssh_user"]])
        if config.get("ssh_password"):
            command.extend(["--ssh-pass", config["ssh_password"]])

        env_merged: Dict[str, str] = {}
        env_merged.update(manifest.get("env") or {})
        env_merged.update(config.get("env") or {})
        env_merged = {k: str(v).replace("{provider_id}", str(provider_id)) for k, v in env_merged.items()}

        internal_port = int(manifest.get("internal_port") or 3000)

        return ContainerSpec(
            image=image,
            command=command or None,
            env=env_merged,
            labels={
                "aladdin.terminal.adapter": "wetty",
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
