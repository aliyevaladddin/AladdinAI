# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""Regression tests for SSH key temp-file handling.

Step 1 scope: SshProxyTransport.enrich() must not create files and must not
return any key path. Key-file helper + wiring live in a separate issue.
"""
from __future__ import annotations

import atexit
import os
import stat
import tempfile
from types import SimpleNamespace

import pytest

from app.services.terminal_transport import key_files
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


def _patch_key_dir(monkeypatch, tmp_path):
    """Point key_files.settings at tmp_path via monkeypatch (no lazy-write)."""
    monkeypatch.setattr(
        key_files, "settings", SimpleNamespace(terminal_ssh_key_dir=str(tmp_path))
    )


def test_get_key_dir_default_and_override(monkeypatch, tmp_path):
    monkeypatch.setattr(
        key_files, "settings", SimpleNamespace(terminal_ssh_key_dir="")
    )
    assert key_files.get_key_dir() == key_files.DEFAULT_KEY_DIR
    _patch_key_dir(monkeypatch, tmp_path)
    assert key_files.get_key_dir() == str(tmp_path)


def test_write_key_file_creates_0600_in_0700_dir(monkeypatch, tmp_path):
    _patch_key_dir(monkeypatch, tmp_path)
    path = key_files.write_key_file("fake-pem-body")
    assert os.path.dirname(path) == str(tmp_path)
    with open(path, encoding="utf-8") as fh:
        assert fh.read() == "fake-pem-body"
    assert stat.S_IMODE(os.lstat(path).st_mode) == 0o600
    assert stat.S_IMODE(os.lstat(str(tmp_path)).st_mode) == 0o700


def test_write_key_file_refuses_symlinked_dir(monkeypatch, tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    os.symlink(str(real), str(link))
    monkeypatch.setattr(
        key_files, "settings", SimpleNamespace(terminal_ssh_key_dir=str(link))
    )
    with pytest.raises(ValueError):
        key_files.write_key_file("fake-pem-body")


def test_remove_key_file_idempotent(monkeypatch, tmp_path):
    _patch_key_dir(monkeypatch, tmp_path)
    path = key_files.write_key_file("fake-pem-body")
    key_files.remove_key_file(path)
    assert not os.path.exists(path)
    # Second removal must not raise.
    key_files.remove_key_file(path)


def test_sweep_removes_leftovers_and_noop_when_missing(monkeypatch, tmp_path):
    _patch_key_dir(monkeypatch, tmp_path)
    stale = tmp_path / "ssh_key_stale.pem"
    stale.write_text("stale", encoding="utf-8")
    other = tmp_path / "keep.txt"
    other.write_text("keep", encoding="utf-8")
    assert key_files.sweep_stale_keys() == 1
    assert not stale.exists()
    assert other.exists()

    missing = tmp_path / "does-not-exist"
    monkeypatch.setattr(
        key_files, "settings", SimpleNamespace(terminal_ssh_key_dir=str(missing))
    )
    assert key_files.sweep_stale_keys() == 0


def test_temporary_key_file_lifecycle(monkeypatch, tmp_path):
    _patch_key_dir(monkeypatch, tmp_path)
    captured_path = None
    with key_files.temporary_key_file("context-manager-pem") as path:
        captured_path = path
        assert os.path.exists(path)
        with open(path, encoding="utf-8") as fh:
            assert fh.read() == "context-manager-pem"
        assert stat.S_IMODE(os.lstat(path).st_mode) == 0o600
    assert not os.path.exists(captured_path)


def test_temporary_key_file_cleans_up_on_exception(monkeypatch, tmp_path):
    _patch_key_dir(monkeypatch, tmp_path)
    captured_path = None
    with pytest.raises(RuntimeError, match="simulated failure"):
        with key_files.temporary_key_file("fail-pem") as path:
            captured_path = path
            assert os.path.exists(path)
            raise RuntimeError("simulated failure")
    assert captured_path is not None
    assert not os.path.exists(captured_path)


def test_get_key_dir_fallback_when_shm_unavailable(monkeypatch):
    monkeypatch.setattr(
        key_files, "settings", SimpleNamespace(terminal_ssh_key_dir="")
    )
    monkeypatch.setattr(os.path, "isdir", lambda path: False if path == "/dev/shm" else True)
    expected = os.path.join(tempfile.gettempdir(), "aladdin-ssh-keys")
    assert key_files.get_key_dir() == expected
