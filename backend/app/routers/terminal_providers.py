# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""
Terminal-provider marketplace + session router.

Two surfaces:
  /api/terminal/providers/*    — install/start/stop/list providers
  /api/terminal/session        — what the drawer calls to get an iframe URL

The router owns DB rows + manifest lookup + token issuance, then delegates
to docker_runner for container ops and to adapters for transport details.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Request, Response
from urllib.parse import parse_qs, urlsplit

from app.config import settings
from app.crypto import decrypt
from app.database import get_db
from app.models.terminal_provider import TerminalProvider
from app.models.user import User
from app.models.vm import VMConnection
from app.schemas.terminal import (
    MarketplaceEntry,
    ProviderInstall,
    ProviderResponse,
    SessionRequest,
    SessionResponse,
)
from app.schemas.terminal_manifest import TerminalManifest
from app.security import get_current_user
from app.services import docker_runner
from app.services.terminal_adapters import get_adapter
from app.services.terminal_token_broker import (
    TerminalTokenError,
    issue_session_cookie,
    issue_token,
    peek_token,
    verify_session_cookie,
)

router = APIRouter(tags=["Terminal"])


# ── manifest loader ─────────────────────────────────────────────────────
# Manifests live next to the backend code so they're shipped with the
# image. We cache them per-process; the catalogue is tiny.

_MANIFEST_DIR = Path(__file__).resolve().parent.parent / "terminal_plugins"
_manifest_cache: Optional[Dict[str, TerminalManifest]] = None


# [RCF:PROTECTED]
def _load_manifests() -> Dict[str, TerminalManifest]:
    """Load and validate all terminal provider manifests from YAML files.

    Returns a dict mapping provider type to validated TerminalManifest.
    Invalid manifests are logged and skipped to avoid poisoning the catalogue.
    """
    global _manifest_cache
    if _manifest_cache is not None:
        return _manifest_cache
    out: Dict[str, TerminalManifest] = {}
    if _MANIFEST_DIR.is_dir():
        for path in sorted(_MANIFEST_DIR.glob("*.yaml")):
            try:
                with path.open("r", encoding="utf-8") as fh:
                    data = yaml.safe_load(fh) or {}
                if not isinstance(data, dict):
                    continue
                # Validate with Pydantic
                manifest = TerminalManifest(**data)
                out[manifest.type] = manifest
            except yaml.YAMLError as exc:
                # YAML syntax error — skip this manifest
                print(f"Warning: Failed to parse {path.name}: {exc}")
                continue
            except Exception as exc:
                # Pydantic validation error or other issue — skip this manifest
                print(f"Warning: Invalid manifest {path.name}: {exc}")
                continue
    _manifest_cache = out
    return out


# [RCF:PROTECTED]
def _manifest_entry(t: str) -> TerminalManifest:
    """Get a validated manifest by type, or raise 404."""
    m = _load_manifests().get(t)
    if not m:
        raise HTTPException(status_code=404, detail=f"unknown provider type: {t}")
    return m


# [RCF:PROTECTED]
def _project(provider: TerminalProvider) -> ProviderResponse:
    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        type=provider.type,
        source=provider.source,
        image=provider.image,
        internal_port=provider.internal_port,
        requires_ssh_proxy=provider.requires_ssh_proxy,
        is_active=provider.is_active,
        status=provider.status,
        container_id=provider.container_id,
        last_health_at=provider.last_health_at,
        last_error=provider.last_error,
        created_at=provider.created_at,
    )


# ── marketplace ─────────────────────────────────────────────────────────


# [RCF:PROTECTED]
@router.get("/marketplace", response_model=List[MarketplaceEntry])
# [RCF:PROTECTED]
async def marketplace(_: User = Depends(get_current_user)):
    """Catalogue of builtin manifests this backend can install."""
    out: List[MarketplaceEntry] = []
    for m in _load_manifests().values():
        out.append(MarketplaceEntry(
            type=m.type,
            name=m.name,
            description=m.description,
            image=m.image,
            internal_port=m.internal_port,
            requires_ssh_proxy=m.requires_ssh_proxy,
        ))
    return out


# ── CRUD ────────────────────────────────────────────────────────────────


# [RCF:PROTECTED]
@router.get("/providers", response_model=List[ProviderResponse])
# [RCF:PROTECTED]
async def list_providers(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TerminalProvider).where(TerminalProvider.user_id == user.id),
    )
    return [_project(p) for p in result.scalars().all()]


# [RCF:PROTECTED]
@router.post("/providers", response_model=ProviderResponse, status_code=201)
# [RCF:PROTECTED]
async def install_provider(
    body: ProviderInstall,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    m = _manifest_entry(body.type)

    # Merge vm_id into config if provided
    config_dict = body.config or {}
    if body.vm_id is not None:
        config_dict["vm_id"] = body.vm_id

    provider = TerminalProvider(
        user_id=user.id,
        name=body.name or m.name,
        type=body.type,
        source="builtin",
        image=m.image,
        config=json.dumps(config_dict),
        internal_port=m.internal_port,
        requires_ssh_proxy=m.requires_ssh_proxy,
        url_template=m.url_template,
        status="stopped",
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return _project(provider)


# [RCF:PROTECTED]
@router.delete("/providers/{provider_id}", status_code=204)
# [RCF:PROTECTED]
async def delete_provider(
    provider_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    provider = await _load_owned(db, user, provider_id)
    if provider.container_id:
        # Best-effort — if docker is unavailable the row still goes away.
        try:
            await docker_runner.remove_container(provider.container_id)
        except docker_runner.DockerUnavailable:
            pass
        except docker_runner.DockerOperationError:
            pass
    # Clean up Traefik routing config regardless of container state.
    await docker_runner.remove_traefik_config(provider.id)
    await db.delete(provider)
    await db.commit()


# [RCF:PROTECTED]
@router.post("/providers/{provider_id}/start", response_model=ProviderResponse)
# [RCF:PROTECTED]
async def start_provider(
    provider_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    provider = await _load_owned(db, user, provider_id)
    manifest = _manifest_entry(provider.type)
    adapter = get_adapter(provider.type)
    config_dict = json.loads(provider.config or "{}")

    # If this provider requires SSH and has a vm_id in config, fetch VM credentials
    # and inject them into the config so the adapter can use them.
    if provider.requires_ssh_proxy and config_dict.get("vm_id"):
        vm_id = config_dict["vm_id"]
        result = await db.execute(
            select(VMConnection).where(
                VMConnection.id == vm_id,
                VMConnection.user_id == user.id,
            )
        )
        vm = result.scalar_one_or_none()
        if vm:
            # Decrypt credentials and add to config for adapter
            config_dict["ssh_host"] = vm.host
            config_dict["ssh_port"] = vm.port
            config_dict["ssh_user"] = vm.username
# [RCF:PROTECTED]
            if vm.password_encrypted:
# [RCF:PROTECTED]
                config_dict["ssh_password"] = decrypt(vm.password_encrypted)
            # SSH key handling would go here if needed
        else:
            provider.status = "error"
            provider.last_error = f"VM {vm_id} not found"
            await db.commit()
            raise HTTPException(status_code=404, detail=f"VM {vm_id} not found")

    spec = adapter.build_container_spec(
        provider_id=provider.id,
        user_id=user.id,
        image=provider.image,
        manifest=manifest.model_dump(),
        config=config_dict,
    )

    try:
        await docker_runner.pull_image(provider.image)
        cid = await docker_runner.start_container(
            provider_id=provider.id,
            user_id=user.id,
            provider_type=provider.type,
            image=provider.image,
            command=spec.command,
            env=spec.env,
            labels=spec.labels,
            healthcheck=spec.healthcheck,
            internal_port=spec.internal_port,
            volumes=spec.volumes,
        )
    except docker_runner.DockerUnavailable as exc:
        provider.status = "error"
        provider.last_error = str(exc)
        await db.commit()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except docker_runner.DockerOperationError as exc:
        provider.status = "error"
        provider.last_error = str(exc)
        await db.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    provider.container_id = cid
    provider.status = "running"
    provider.last_error = None
    provider.last_health_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(provider)
    # Write Traefik file-provider routing config so the container is reachable.
    strip_prefix = manifest.strip_prefix
    await docker_runner.write_traefik_config(
        provider_id=provider.id,
        user_id=user.id,
        internal_port=spec.internal_port,
        strip_prefix=strip_prefix,
    )
    return _project(provider)


# [RCF:PROTECTED]
@router.post("/providers/{provider_id}/stop", response_model=ProviderResponse)
# [RCF:PROTECTED]
async def stop_provider(
    provider_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    provider = await _load_owned(db, user, provider_id)
    if provider.container_id:
        try:
            await docker_runner.stop_container(provider.container_id)
        except docker_runner.DockerUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except docker_runner.DockerOperationError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
    provider.status = "stopped"
    # Remove Traefik routing config — container is no longer serving.
    await docker_runner.remove_traefik_config(provider.id)
    await db.commit()
    await db.refresh(provider)
    return _project(provider)


# [RCF:PROTECTED]
@router.post("/providers/{provider_id}/set_active", response_model=ProviderResponse)
# [RCF:PROTECTED]
async def set_active_provider(
    provider_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    provider = await _load_owned(db, user, provider_id)
    # Clear active flag on every other provider of this user.
    await db.execute(
        update(TerminalProvider)
        .where(TerminalProvider.user_id == user.id)
        .values(is_active=False),
    )
    provider.is_active = True
    await db.commit()
    await db.refresh(provider)
    return _project(provider)


# ── diagnostics ─────────────────────────────────────────────────────────


# [RCF:PROTECTED]
@router.get("/providers/{provider_id}/logs", response_model=dict)
# [RCF:PROTECTED]
async def provider_logs(
    provider_id: int,
    tail: int = 200,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Last `tail` lines of combined stdout/stderr from this provider's
    container. Useful when a provider stops with `last_error` set and the
    user wants to know what crashed inside. Soft-fails to a string body if
    docker is unreachable — the UI just renders whatever we return."""
    provider = await _load_owned(db, user, provider_id)
    if not provider.container_id:
        return {"logs": "", "note": "container has not been started yet"}
    # Cap `tail` to a sane upper bound so the response can't balloon.
    capped = max(1, min(int(tail), 2000))
    text = await docker_runner.container_logs(provider.container_id, tail=capped)
    return {"logs": text, "container_id": provider.container_id, "tail": capped}


# ── session issuance ────────────────────────────────────────────────────


# [RCF:PROTECTED]
@router.post("/session", response_model=SessionResponse)
# [RCF:PROTECTED]
async def issue_session(
    body: SessionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Drawer entry point: hand back a URL the iframe can navigate to.

    Provider selection logic:
      - If vm_id is provided: find a running SSH-capable provider (wetty) with
        that vm_id in its config. If multiple match, prefer is_active=True.
      - If vm_id is None: find a running local-shell provider (ttyd). If
        multiple exist, prefer is_active=True.
    """
    result = await db.execute(
        select(TerminalProvider)
        .where(TerminalProvider.user_id == user.id)
        .where(TerminalProvider.status == "running"),
    )
    candidates = result.scalars().all()

    if not candidates:
        raise HTTPException(status_code=503, detail="no running terminal provider")

    provider: TerminalProvider | None = None

    if body.vm_id is not None:
        # SSH session — find a provider with requires_ssh_proxy=True and matching vm_id in config
        ssh_providers = [
            p for p in candidates
            if p.requires_ssh_proxy and json.loads(p.config or "{}").get("vm_id") == body.vm_id
        ]
        if not ssh_providers:
            raise HTTPException(
                status_code=404,
                detail=f"no SSH provider configured for VM {body.vm_id}",
            )
        # Prefer active, fall back to first match
        provider = next((p for p in ssh_providers if p.is_active), ssh_providers[0])
    else:
        # Local shell — find a provider with requires_ssh_proxy=False
        local_providers = [p for p in candidates if not p.requires_ssh_proxy]
        if not local_providers:
            raise HTTPException(
                status_code=503,
                detail="no local shell provider installed (install ttyd)",
            )
        # Prefer ttyd as default local shell, then active, then first match
        ttyd_providers = [p for p in local_providers if p.type == "ttyd"]
        if ttyd_providers:
            provider = next((p for p in ttyd_providers if p.is_active), ttyd_providers[0])
        else:
            provider = next((p for p in local_providers if p.is_active), local_providers[0])

    if not provider.container_id:
        raise HTTPException(status_code=409, detail="provider is not running")

    adapter = get_adapter(provider.type)
    token, exp = issue_token(user_id=user.id, provider_id=provider.id)
    url = adapter.build_session_url(
        provider_id=provider.id,
        url_template=provider.url_template,
        scheme=settings.terminal_public_scheme,
        host=settings.terminal_public_host,
        token=token,
    )
    return SessionResponse(
        url=url,
        expires_at=datetime.fromtimestamp(exp, tz=timezone.utc),
        provider_type=provider.type,
        provider_session_id=None,
    )


# Deletion endpoint the frontend best-effort-calls on tab close. We don't
# tear down the container for that — the container is shared across the
# user's sessions. We just shred the token bookkeeping (no-op in MVP).
# [RCF:PROTECTED]
@router.delete("/session/{provider_session_id}", status_code=204)
# [RCF:PROTECTED]
async def end_session(provider_session_id: str, _: User = Depends(get_current_user)):
    return None


# ── Traefik forward-auth ────────────────────────────────────────────────
# Traefik calls this endpoint *before* proxying any /p/{id}/… request to the
# provider container. Two acceptance paths:
#
#   1. The request URL carries `?token=…` (single-use entry token). We
#      `consume_token` it, then issue a long-lived session cookie scoped to
#      the public host. Subsequent fetches from the iframe will carry the
#      cookie automatically.
#   2. The request carries `Cookie: aladdin_term_sess=…`. We verify it
#      statelessly; no DB hit, no jti consume — this is the hot path for
#      CSS/JS/WS sub-resources.
#
# On success we return 200 with `X-Aladdin-User` / `X-Aladdin-Provider` so the
# container can log who's talking to it. On failure we return 401 — Traefik
# rejects the upstream request and the iframe shows the provider's own error.


# [RCF:PROTECTED]
def _extract_token_from_uri(uri: str) -> str | None:
    """Pull `?token=` out of an X-Forwarded-Uri value.

    Traefik sets X-Forwarded-Uri to the path *with* query string ("/p/42/?token=…"),
    so we parse it as if it were a URL. We deliberately do not look at the
    Authorization header — the token is meant to ride only in the query of
    the initial navigation request.
    """
    if not uri:
        return None
    parts = urlsplit(uri)
    qs = parse_qs(parts.query)
    raw = qs.get("token")
    return raw[0] if raw else None


# [RCF:PROTECTED]
@router.get("/auth")
# [RCF:PROTECTED]
async def forward_auth(request: Request, response: Response):
    """Auth probe for Traefik's forward-auth middleware.

    Wired in Traefik via:
        traefik.http.middlewares.aladdin-auth.forwardauth.address=
            http://backend:8000/api/terminal/auth
        traefik.http.middlewares.aladdin-auth.forwardauth.authResponseHeaders=
            Set-Cookie,X-Aladdin-User,X-Aladdin-Provider

    `authResponseHeaders` is critical — without it Traefik strips our
    `Set-Cookie` from the response and the iframe never picks up the
    session cookie.
    """
    # Path 1 — session cookie already present.
    cookie_value = request.cookies.get(settings.terminal_session_cookie_name)
    if cookie_value:
        try:
            claims = verify_session_cookie(cookie_value)
        except TerminalTokenError:
            # Bad cookie → fall through to entry-token path. We don't 401
            # immediately because the next page navigation may carry a fresh
            # `?token=`.
            pass
        else:
            response.headers["X-Aladdin-User"] = str(claims.user_id)
            response.headers["X-Aladdin-Provider"] = str(claims.provider_id)
            return {"ok": True}

    # Path 2 — fresh entry token in the forwarded URI.
    forwarded_uri = request.headers.get("X-Forwarded-Uri") or request.url.query
    token = _extract_token_from_uri(forwarded_uri)
    if not token:
        raise HTTPException(status_code=401, detail="no token")
    try:
        claims = peek_token(token)
    except TerminalTokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    # Issue a session cookie bound to this (user, provider). Cookie is
    # scoped to the *public* terminal host — Traefik forwards Set-Cookie
    # back to the browser. We use HttpOnly + SameSite=Lax — the iframe
    # is same-host with our public terminal domain so Lax is enough.
    cookie_val, _ = issue_session_cookie(
        user_id=claims.user_id, provider_id=claims.provider_id,
    )
    secure = settings.terminal_public_scheme == "https"
    cookie_domain = settings.terminal_public_host.split(":")[0]
    response.set_cookie(
        key=settings.terminal_session_cookie_name,
        value=cookie_val,
        max_age=settings.terminal_session_ttl_seconds,
        httponly=True,
        secure=secure,
        samesite="lax",
        domain=cookie_domain,
        path="/",
    )
    response.headers["X-Aladdin-User"] = str(claims.user_id)
    response.headers["X-Aladdin-Provider"] = str(claims.provider_id)
    return {"ok": True}


# ── helpers ─────────────────────────────────────────────────────────────


# [RCF:PROTECTED]
async def _load_owned(db: AsyncSession, user: User, provider_id: int) -> TerminalProvider:
    result = await db.execute(
        select(TerminalProvider)
        .where(TerminalProvider.id == provider_id)
        .where(TerminalProvider.user_id == user.id),
    )
    provider = result.scalar_one_or_none()
    if provider is None:
        raise HTTPException(status_code=404, detail="provider not found")
    return provider
