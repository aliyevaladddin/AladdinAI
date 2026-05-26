# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""
Local shell transport — shell runs inside the container.

Used by ttyd and similar providers that don't need external connection
parameters. The transport is a no-op: it returns empty enrichment because
the adapter already has everything it needs from the manifest.
"""

from __future__ import annotations

from app.services.terminal_transport.base import (
    TransportContext,
    TransportEnrichment,
    TransportLayer,
)


class LocalShellTransport(TransportLayer):
    """Transport for providers that run a shell inside their own container."""

    async def enrich(self, ctx: TransportContext) -> TransportEnrichment:
        """No enrichment needed — the adapter spec is complete as-is."""
        return TransportEnrichment()
