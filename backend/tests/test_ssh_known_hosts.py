# NOTICE: This file is protected under RCF-PL
"""Tests for the SSH known_hosts TOFU helper (issue #356)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.services.ssh_known_hosts import resolve_known_hosts


def test_resolve_known_hosts_creates_file_when_missing(tmp_path: Path):
    """If ~/.ssh/known_hosts does not exist, it should be created."""
    fake_path = tmp_path / ".ssh" / "known_hosts"
    with patch("app.services.ssh_known_hosts._KNOWN_HOSTS_PATH", fake_path):
        result = resolve_known_hosts()

    assert result == str(fake_path)
    assert fake_path.exists(), "known_hosts file should have been created"


def test_resolve_known_hosts_returns_existing_file(tmp_path: Path):
    """If ~/.ssh/known_hosts already exists, its path is returned as-is."""
    fake_path = tmp_path / ".ssh" / "known_hosts"
    fake_path.parent.mkdir(parents=True)
    fake_path.write_text("example.com ssh-ed25519 AAAA...\n")

    with patch("app.services.ssh_known_hosts._KNOWN_HOSTS_PATH", fake_path):
        result = resolve_known_hosts()

    assert result == str(fake_path)
    assert fake_path.read_text().startswith("example.com")


def test_resolve_known_hosts_fallback_on_oserror():
    """If mkdir/touch raises, should fall back to /dev/null."""
    with patch("app.services.ssh_known_hosts._KNOWN_HOSTS_PATH") as mock_path:
        mock_path.parent.mkdir.side_effect = OSError("read-only filesystem")
        result = resolve_known_hosts()

    assert result == "/dev/null"
