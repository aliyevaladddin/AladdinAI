# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""
SSH proxy transport — container acts as SSH client to a remote VM.

Used by wetty and similar providers that need to connect to an external
machine via SSH. The transport:
  1. Resolves vm_id -> VM record from the database
  2. Decrypts SSH credentials (password or key)
  3. Injects connection parameters into the container spec

The SSH broker is the only place that reads VM credentials and decrypts them.
Adapters stay pure and never see secrets.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select

from app.crypto import decrypt
from app.database import get_db
from app.models.vm import VMConnection
from app.services.terminal_transport.base import (
    TransportContext,
    TransportEnrichment,
    TransportLayer,
)


class SshProxyTransport(TransportLayer):
    """Transport for providers that SSH into a remote VM."""

    async def enrich(self, ctx: TransportContext) -> TransportEnrichment:
        """Resolve VM credentials and inject SSH parameters.

        Args:
            ctx: Must include vm_id

        Returns:
            Enrichment with SSH connection parameters

        Raises:
            ValueError: If vm_id is missing or VM not found
            RuntimeError: If decryption fails
        """
        if not ctx.vm_id:
            raise ValueError("SshProxyTransport requires vm_id in context")

        # Fetch VM record
        vm = await self._get_vm(ctx.vm_id, ctx.user_id)
        if not vm:
            raise ValueError(f"VM {ctx.vm_id} not found or not owned by user {ctx.user_id}")

        # Decrypt credentials
        ssh_password: Optional[str] = None
        ssh_key: Optional[str] = None

        if vm.password_encrypted:
            try:
                ssh_password = decrypt(vm.password_encrypted)
            except Exception as exc:
                raise RuntimeError(f"Failed to decrypt SSH password for VM {ctx.vm_id}: {exc}") from exc

        if vm.ssh_key_encrypted:
            try:
                ssh_key = decrypt(vm.ssh_key_encrypted)
            except Exception as exc:
                raise RuntimeError(f"Failed to decrypt SSH key for VM {ctx.vm_id}: {exc}") from exc

        # Build enrichment
        labels = {
            "aladdin.terminal.transport": "ssh-proxy",
            "aladdin.terminal.vm_id": str(ctx.vm_id),
        }

        # SSH parameters go into config dict that the adapter will read
        # (wetty adapter already knows how to inject --ssh-host etc from config)
        config_overrides = {
            "ssh_host": vm.host,
            "ssh_port": vm.port or 22,
            "ssh_user": vm.username or "root",
        }

        if ssh_password:
            config_overrides["ssh_password"] = ssh_password
        if ssh_key:
            # For key-based auth, we'd write the key to a temp file or pass via env
            # For now, wetty only supports password auth via --ssh-pass
            # TODO: implement key-based auth when needed
            pass

        # Return enrichment — router will merge config into adapter's config
        return TransportEnrichment(
            config=config_overrides,
            env={},
            labels=labels,
        )

    async def _get_vm(self, vm_id: int, user_id: int) -> Optional[VMConnection]:
        """Fetch VM record from database."""
        async for db in get_db():
            result = await db.execute(
                select(VMConnection).where(VMConnection.id == vm_id, VMConnection.user_id == user_id)
            )
            return result.scalar_one_or_none()
        return None
