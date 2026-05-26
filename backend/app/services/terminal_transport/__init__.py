# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""
Transport layer for terminal providers.

Transports define HOW a terminal connects to its target:
  - LocalShellTransport: shell inside container (ttyd)
  - SshProxyTransport: SSH to remote VM (wetty)

Usage in router:
    transport = LocalShellTransport()  # or SshProxyTransport()
    ctx = TransportContext(provider_id=1, user_id=1, vm_id=42)
    enrichment = await transport.enrich(ctx)
    # Merge enrichment.config into adapter config
    # Merge enrichment.env into container env
    # Merge enrichment.labels into container labels
"""

from app.services.terminal_transport.base import (
    TransportContext,
    TransportEnrichment,
    TransportLayer,
)
from app.services.terminal_transport.local_shell import LocalShellTransport
from app.services.terminal_transport.ssh_proxy import SshProxyTransport

__all__ = [
    "TransportLayer",
    "TransportContext",
    "TransportEnrichment",
    "LocalShellTransport",
    "SshProxyTransport",
]
