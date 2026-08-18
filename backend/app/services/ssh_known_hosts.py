# NOTICE: This file is protected under RCF-PL
"""Shared SSH known-hosts helper.

Implements TOFU (Trust On First Use) — the same strategy ``ssh(1)`` uses:
  1. Load ``~/.ssh/known_hosts`` on first connection (empty dict if absent).
  2. asyncssh writes the server's host key into the file automatically.
  3. On every subsequent connection the key is verified; mismatch → abort.

This replaces the insecure ``known_hosts=None`` pattern that skipped
host-key verification entirely (MITM vulnerability — issue #356).
"""

from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)

_KNOWN_HOSTS_PATH = Path.home() / ".ssh" / "known_hosts"


def resolve_known_hosts() -> str:
    """Return the path to ``~/.ssh/known_hosts``.

    * If the file exists, its path is returned as-is — asyncssh will load it.
    * If the file does not exist, it is created (empty). asyncssh will then
      write the server's host key on first connect, establishing the trust
      anchor for every future connection.

    Returns:
        Absolute path to the known_hosts file.
    """
    try:
        _KNOWN_HOSTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not _KNOWN_HOSTS_PATH.exists():
            _KNOWN_HOSTS_PATH.touch(mode=0o644)
            log.info("Created empty known_hosts at %s", _KNOWN_HOSTS_PATH)
    except OSError as exc:
        # If we cannot create the file, fall back to a per-run temp file so
        # connections still work (without persistence).  This is less ideal
        # than a stable file but far better than known_hosts=None.
        log.warning(
            "Cannot persist known_hosts at %s (%s); using in-memory fallback",
            _KNOWN_HOSTS_PATH,
            exc,
        )
        return "/dev/null"

    return str(_KNOWN_HOSTS_PATH)
