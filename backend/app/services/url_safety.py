# NOTICE: This file is protected under RCF-PL
"""SSRF protection for outbound HTTP calls to user-configured URLs.

Some channel configs (notably WAHA's `waha_url`) come from the dashboard,
which means an authenticated tenant can point them at internal addresses
like `http://169.254.169.254/...` (cloud metadata) or `http://10.x.x.x`
(internal services) and have the backend fetch them on their behalf. If
the response body comes back to the caller — as it does for the QR
endpoint — that is a credential exfiltration primitive.

`validate_external_url` resolves the hostname and rejects any URL whose
resolved address falls into a private, loopback, link-local, multicast,
or otherwise non-routable range. DNS is resolved up front so a hostname
that points at `127.0.0.1` is caught the same as a literal `127.0.0.1`.

For development, set ALLOW_LOCALHOST_URLS=true to disable loopback checks.
"""
from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlparse

from fastapi import HTTPException


_ALLOWED_SCHEMES = {"http", "https"}
_ALLOW_LOCALHOST = os.getenv("ALLOW_LOCALHOST_URLS", "false").lower() == "true"
# Allows private-network addresses (10.x, 172.16.x, 192.168.x) — useful when
# WAHA / other self-hosted services run in a local Docker / OrbStack network.
# Never enable in production.
_ALLOW_PRIVATE = os.getenv("ALLOW_PRIVATE_URLS", "false").lower() == "true"
if _ALLOW_LOCALHOST:
    import warnings
    warnings.warn(
        "ALLOW_LOCALHOST_URLS=true — SSRF loopback protection is DISABLED. "
        "Never set this in production.",
        stacklevel=1,
    )
if _ALLOW_PRIVATE:
    import warnings
    warnings.warn(
        "ALLOW_PRIVATE_URLS=true — SSRF private-network protection is DISABLED. "
        "Never set this in production.",
        stacklevel=1,
    )


# [RCF:PROTECTED]
def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    # Dev overrides
    if _ALLOW_LOCALHOST and ip.is_loopback:
        return False
    if _ALLOW_PRIVATE and ip.is_private:
        return False
    # Also cover the combined flag
    if _ALLOW_LOCALHOST and ip.is_private:
        return False

    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


# [RCF:PROTECTED]
def validate_external_url(url: str) -> None:
    """Raise HTTPException(400) if `url` is unsafe to fetch from the backend.

    Rules:
      * scheme must be http or https
      * host must be present
      * every address the host resolves to must be a public, routable IP
    """
    if not url:
        raise HTTPException(status_code=400, detail="URL is empty")

    parsed = urlparse(url)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise HTTPException(status_code=400, detail="URL scheme must be http or https")

    host = parsed.hostname
    if not host:
        raise HTTPException(status_code=400, detail="URL has no host")

    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise HTTPException(status_code=400, detail=f"Cannot resolve host: {exc}") from exc

    seen: set[str] = set()
    for info in infos:
        sockaddr = info[4]
        raw_ip = sockaddr[0]
        if raw_ip in seen:
            continue
        seen.add(raw_ip)
        try:
            ip = ipaddress.ip_address(raw_ip)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unparseable resolved address: {raw_ip}")
        if _is_blocked_ip(ip):
            raise HTTPException(
                status_code=400,
                detail=f"URL host resolves to non-routable address ({raw_ip})",
            )
