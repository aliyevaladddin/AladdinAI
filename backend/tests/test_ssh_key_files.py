# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""Regression tests for SSH key temp-file handling.

Step 1 scope: SshProxyTransport.enrich() must not create files and must not
return any key path. Key-file helper + wiring live in a separate issue.
"""
from __future__ import annotations

import atexit
import os
import tempfile
from types import SimpleNamespace

import pytest

from app.services.terminal_transport.base import TransportContext
from app.services.terminal_transport.ssh_proxy import SshProxyTransport


@pytest.mark.asyncio
async def test_enrich_creates_no_files_and_returns_no_key_path(monkeypatch, tmp_path):
    """enrich() returns host/port/user only — no temp file, no key path."""
    # Route any tempfile creation into tmp_path so a regression is contained
    # and detectable. Uses monkeypatch (no lazy-write).
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setenv("TEMP", str(tmp_path))
    monkeypatch.setenv("TMP", str(tmp_path))

    # Fail loudly if enrich() tries the old eager-write path.
    def _forbid_tempfile(*args, **kwargs):
        raise AssertionError("enrich() must not create a temp file")

    def _forbid_chmod(*args, **kwargs):
        raise AssertionError("enrich() must not chmod any key file")

    def _forbid_atexit(*args, **kwargs):
        raise AssertionError("enrich() must not register atexit cleanup")

    monkeypatch.setattr(tempfile, "NamedTemporaryFile", _forbid_tempfile)
    monkeypatch.setattr(os, "chmod", _forbid_chmod)
    monkeypatch.setattr(atexit, "register", _forbid_atexit)

    # Fake VM row — includes an encrypted key to prove it is ignored.
    fake_vm = SimpleNamespace(
        host="192.0.2.10",
        port=2222,
        username="deploy",
        password_encrypted="plaintext-password",
        ssh_key_encrypted="fake-private-key-material",
    )

    async def _fake_get_vm(self, vm_id, user_id):
        assert vm_id == 42
        assert user_id == 7
        return fake_vm

    monkeypatch.setattr(SshProxyTransport, "_get_vm", _fake_get_vm)

    transport = SshProxyTransport()
    ctx = TransportContext(provider_id=1, user_id=7, vm_id=42)

    before = set(tmp_path.iterdir())
    enrichment = await transport.enrich(ctx)
    after = set(tmp_path.iterdir())

    assert after == before, f"enrich() created files: {after - before}"
    assert "ssh_key_file" not in enrichment.config
    assert "SSH_KEY_FILE" not in enrichment.env
    assert enrichment.env == {}
    assert enrichment.config["ssh_host"] == "192.0.2.10"
    assert enrichment.config["ssh_port"] == 2222
    assert enrichment.config["ssh_user"] == "deploy"
