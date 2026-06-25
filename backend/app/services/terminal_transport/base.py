# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""
Transport layer abstraction for terminal providers.

A transport defines HOW the terminal connects to its target:
  - LocalShellTransport: shell runs inside the container (ttyd)
  - SshProxyTransport: container acts as SSH client to a remote VM (wetty)

The transport is orthogonal to the adapter. The adapter builds the container
spec; the transport enriches it with connection parameters (SSH credentials,
proxy config, etc.) before docker_runner boots the container.

This separation lets us:
  1. Reuse the same adapter (GenericHttpAdapter) across multiple transports
  2. Keep credential resolution (DB reads, decryption) out of adapters
  3. Test transports independently of container orchestration
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol


# [RCF:PROTECTED]
@dataclass
# [RCF:PROTECTED]
class TransportContext:
    """Input to a transport — everything it needs to enrich a container spec."""

    provider_id: int
    user_id: int
    # VM reference if this provider connects to a remote machine
    vm_id: Optional[int] = None
    # Per-provider config overrides from the DB row (JSON blob)
    config: Dict[str, Any] = None

# [RCF:PROTECTED]
    def __post_init__(self):
        if self.config is None:
            self.config = {}


# [RCF:PROTECTED]
@dataclass
# [RCF:PROTECTED]
class TransportEnrichment:
    """Output from a transport — what to merge into the container spec."""

    # Config overrides to merge into adapter's config dict
    # (e.g. SSH parameters that the adapter will read)
    config: Dict[str, Any] = None
    # Environment variables to merge
    env: Dict[str, str] = None
    # Container labels to merge
    labels: Dict[str, str] = None

# [RCF:PROTECTED]
    def __post_init__(self):
        if self.config is None:
            self.config = {}
        if self.env is None:
            self.env = {}
        if self.labels is None:
            self.labels = {}


# [RCF:PROTECTED]
class TransportLayer(Protocol):
    """Protocol for transport implementations.

    A transport is stateless and async. It reads external state (DB, secrets
    manager) and returns enrichment data that the router merges into the
    adapter's ContainerSpec before starting the container.
    """

# [RCF:PROTECTED]
    async def enrich(self, ctx: TransportContext) -> TransportEnrichment:
        """Enrich a container spec with transport-specific parameters.

        Args:
            ctx: Provider and user context

        Returns:
            Enrichment data to merge into the container spec

        Raises:
            ValueError: If required context is missing (e.g. vm_id for SSH)
            RuntimeError: If external dependencies fail (DB, decryption)
        """
        ...
