# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""Filesystem helper for SSH private-key files.

Not wired to any transport yet — wetty key support lives in a separate
feature issue. This module only centralises the safe create/remove/sweep
primitives so the eager ``tempfile`` write in ``ssh_proxy.py`` stays deleted.

Security properties:
  - Key directory defaults to tmpfs (``/dev/shm/aladdin-ssh-keys``), mode 0700.
  - Key files are created with ``mkstemp`` (0600 at creation), never chmod-after.
  - Symlinked directories are refused (checked with ``os.lstat``, not ``stat``).
"""
from __future__ import annotations

import contextlib
import logging
import os
import stat
import tempfile
from typing import Iterator

from app.config import settings

log = logging.getLogger(__name__)

__all__ = [
    "DEFAULT_KEY_DIR",
    "get_key_dir",
    "write_key_file",
    "remove_key_file",
    "temporary_key_file",
    "sweep_stale_keys",
]

DEFAULT_KEY_DIR = "/dev/shm/aladdin-ssh-keys"


def get_key_dir() -> str:
    """Return the configured key directory, tmpfs default, or secure temp fallback."""
    configured = getattr(settings, "terminal_ssh_key_dir", "") or ""
    configured = configured.strip()
    if configured:
        return configured
    if os.path.isdir("/dev/shm") and os.access("/dev/shm", os.W_OK):
        return DEFAULT_KEY_DIR
    return os.path.join(tempfile.gettempdir(), "aladdin-ssh-keys")


def _ensure_key_dir(path: str) -> str:
    """Create the key dir (0700) and refuse symlinks / wrong owners."""
    os.makedirs(path, mode=0o700, exist_ok=True)
    st = os.lstat(path)
    if stat.S_ISLNK(st.st_mode):
        raise ValueError(f"SSH key dir must not be a symlink: {path}")
    if not stat.S_ISDIR(st.st_mode):
        raise ValueError(f"SSH key dir is not a directory: {path}")
    if st.st_uid != os.getuid():
        raise ValueError(
            f"SSH key dir owned by uid {st.st_uid}, expected {os.getuid()}: {path}"
        )
    # makedirs mode is a no-op when the dir already exists — enforce 0700.
    current = stat.S_IMODE(st.st_mode)
    if current != 0o700:
        os.chmod(path, 0o700)
    return path


def write_key_file(pem: str) -> str:
    """Write PEM text to a 0600 file inside the 0700 key dir. Return the path."""
    if not pem:
        raise ValueError("write_key_file requires non-empty PEM text")
    key_dir = _ensure_key_dir(get_key_dir())
    fd, tmp_path = tempfile.mkstemp(prefix="ssh_key_", suffix=".pem", dir=key_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(pem)
        os.chmod(tmp_path, 0o600)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    log.info("Wrote SSH key file: %s", tmp_path)
    return tmp_path


def remove_key_file(path: str) -> None:
    """Delete a key file; ignore it if already gone."""
    if not path:
        return
    try:
        os.unlink(path)
    except FileNotFoundError:
        return
    log.info("Removed SSH key file: %s", path)


@contextlib.contextmanager
def temporary_key_file(pem: str) -> Iterator[str]:
    """Context manager to safely create a temporary key file and guarantee its removal."""
    path = write_key_file(pem)
    try:
        yield path
    finally:
        remove_key_file(path)


def sweep_stale_keys() -> int:
    """Delete leftover ``ssh_key_*.pem`` files. No-op when dir is missing."""
    key_dir = get_key_dir()
    try:
        st = os.lstat(key_dir)
    except FileNotFoundError:
        return 0
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        log.warning("Skipping SSH key sweep: not a directory: %s", key_dir)
        return 0
    removed = 0
    for name in os.listdir(key_dir):
        if not (name.startswith("ssh_key_") and name.endswith(".pem")):
            continue
        full = os.path.join(key_dir, name)
        try:
            # Never follow symlinks during sweep.
            if stat.S_ISLNK(os.lstat(full).st_mode):
                log.warning("Skipping symlinked key file during sweep: %s", full)
                continue
            os.unlink(full)
            removed += 1
        except FileNotFoundError:
            continue
        except OSError:
            log.warning("Failed to remove stale key file: %s", full, exc_info=True)
    if removed:
        log.info("Swept %d stale SSH key file(s) in %s", removed, key_dir)
    return removed
