# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""
Single-use, short-lived tokens for handing terminal sessions to the iframe.

Design constraints:
  * Verifiable without a DB round-trip — the token carries a signed payload
    so a Traefik forward-auth middleware can validate it in-band.
  * Single-use — once a session iframe has consumed the token, replays are
    rejected. We track consumption by jti in an in-process dict guarded by
    an asyncio.Lock; the TTL of the entry matches the token's own TTL so
    the dict can't grow unboundedly.
  * Stateless across restarts is **not** a requirement here — we'd rather
    invalidate every outstanding session on a backend restart than persist
    consumed-jti state. The frontend already knows how to reconnect.

Wire format is a compact HMAC token, not a JWT — we don't need the JWT
header indirection and we don't want third parties decoding it.

  token = b64url(payload_json) + "." + b64url(hmac_sha256(payload_json))
  payload = { "uid": user_id, "pid": provider_id, "exp": unix_ts, "jti": uuid4hex }

This keeps the dependency surface to the stdlib — no PyJWT for MVP.
"""

from __future__ import annotations

import asyncio
import base64
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from hashlib import sha256
from typing import Dict

from app.config import settings


@dataclass(frozen=True)
class TerminalTokenClaims:
    user_id: int
    provider_id: int
    expires_at: int   # unix seconds
    jti: str


class TerminalTokenError(Exception):
    """Raised when a token is malformed, expired, replayed, or signature-invalid."""


_consumed: Dict[str, int] = {}   # jti -> exp; entries past exp are GC'd lazily
_lock = asyncio.Lock()


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _sign(payload_b64: str) -> str:
    sig = hmac.new(
        settings.terminal_token_secret.encode("utf-8"),
        payload_b64.encode("ascii"),
        sha256,
    ).digest()
    return _b64url_encode(sig)


def issue_token(*, user_id: int, provider_id: int) -> tuple[str, int]:
    """Mint a fresh single-use session token.

    Returns (token, expires_at_unix_seconds).
    """
    exp = int(time.time()) + max(60, settings.terminal_token_ttl_seconds)
    jti = secrets.token_hex(16)
    payload = {"uid": user_id, "pid": provider_id, "exp": exp, "jti": jti}
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    payload_b64 = _b64url_encode(payload_json.encode("utf-8"))
    return f"{payload_b64}.{_sign(payload_b64)}", exp


def _parse(token: str) -> tuple[str, dict]:
    """Split + signature-verify; return (payload_b64, payload_dict)."""
    if not token or "." not in token:
        raise TerminalTokenError("malformed token")
    payload_b64, sig_b64 = token.split(".", 1)
    expected = _sign(payload_b64)
    # `hmac.compare_digest` to avoid timing oracles on the signature.
    if not hmac.compare_digest(expected, sig_b64):
        raise TerminalTokenError("bad signature")
    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise TerminalTokenError("malformed payload") from exc
    if not isinstance(payload, dict):
        raise TerminalTokenError("malformed payload")
    return payload_b64, payload


def _gc_consumed_locked(now: int) -> None:
    """Drop already-expired jti entries. Caller must hold `_lock`."""
    if len(_consumed) < 64:
        return
    expired = [j for j, exp in _consumed.items() if exp <= now]
    for j in expired:
        _consumed.pop(j, None)


async def consume_token(token: str) -> TerminalTokenClaims:
    """Verify + single-use-consume a token. Raises TerminalTokenError on any failure."""
    _, payload = _parse(token)
    try:
        uid = int(payload["uid"])
        pid = int(payload["pid"])
        exp = int(payload["exp"])
        jti = str(payload["jti"])
    except (KeyError, TypeError, ValueError) as exc:
        raise TerminalTokenError("missing claims") from exc

    now = int(time.time())
    if now >= exp:
        raise TerminalTokenError("token expired")

    async with _lock:
        _gc_consumed_locked(now)
        if jti in _consumed:
            raise TerminalTokenError("token already used")
        _consumed[jti] = exp

    return TerminalTokenClaims(user_id=uid, provider_id=pid, expires_at=exp, jti=jti)


def peek_token(token: str) -> TerminalTokenClaims:
    """Verify signature + expiry WITHOUT marking the token consumed.

    Used by tests and by future admin endpoints; the session endpoint always
    goes through `consume_token` instead.
    """
    _, payload = _parse(token)
    try:
        uid, pid, exp, jti = int(payload["uid"]), int(payload["pid"]), int(payload["exp"]), str(payload["jti"])
    except (KeyError, TypeError, ValueError) as exc:
        raise TerminalTokenError("missing claims") from exc
    if int(time.time()) >= exp:
        raise TerminalTokenError("token expired")
    return TerminalTokenClaims(user_id=uid, provider_id=pid, expires_at=exp, jti=jti)


def _reset_for_tests() -> None:
    """Internal — clear in-process state between tests."""
    _consumed.clear()


# ── session cookies (longer-lived, not single-use) ──────────────────────
# After the iframe's first request consumes a one-time token, Traefik forward
# -auth issues a cookie so the same iframe can fetch CSS/JS/WS without burning
# another token per request. The cookie carries (uid, pid, exp) — no jti —
# and is verified statelessly on every subsequent /p/{pid} request.

@dataclass(frozen=True)
class TerminalSessionClaims:
    user_id: int
    provider_id: int
    expires_at: int


def issue_session_cookie(*, user_id: int, provider_id: int) -> tuple[str, int]:
    """Mint a session-cookie value bound to (user_id, provider_id).

    Lives much longer than the entry token (default 1h) because it's the only
    auth carrier for every request the iframe makes after the first one.
    Returns (cookie_value, expires_at_unix_seconds).
    """
    exp = int(time.time()) + max(60, settings.terminal_session_ttl_seconds)
    payload = {"kind": "sess", "uid": user_id, "pid": provider_id, "exp": exp}
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    payload_b64 = _b64url_encode(payload_json.encode("utf-8"))
    return f"{payload_b64}.{_sign(payload_b64)}", exp


def verify_session_cookie(cookie: str) -> TerminalSessionClaims:
    """Verify signature + expiry of a session cookie. Raises on failure.

    Stateless — we don't track consumed cookies; if leaked, the leak window is
    bounded by `terminal_session_ttl_seconds`. The TTL is short enough that
    this is acceptable for MVP; rotation lands when the Go-side proxy does.
    """
    _, payload = _parse(cookie)
    if payload.get("kind") != "sess":
        raise TerminalTokenError("not a session cookie")
    try:
        uid = int(payload["uid"])
        pid = int(payload["pid"])
        exp = int(payload["exp"])
    except (KeyError, TypeError, ValueError) as exc:
        raise TerminalTokenError("missing claims") from exc
    if int(time.time()) >= exp:
        raise TerminalTokenError("cookie expired")
    return TerminalSessionClaims(user_id=uid, provider_id=pid, expires_at=exp)
