# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""
Terminal provider — pluggable web-based terminal installed by the user from
the in-dashboard marketplace.

One row = one installed provider for one user. Each row maps 1:1 to a Docker
container that we manage on the remote daemon. The frontend doesn't own the
terminal anymore — it just embeds whatever URL we hand back from
`POST /api/terminal/session`.

`config` is a JSON blob carrying per-type knobs (env overrides, the user's
chosen image tag, optional SSH-proxy hints) — we keep it `Text` so this
schema works on both Postgres and SQLite.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TerminalProvider(Base):
    __tablename__ = "terminal_providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    # Display name in the UI (user-editable). Distinct from `type`.
    name: Mapped[str] = mapped_column(String(255))

    # Adapter identifier — ttyd / wetty / guacamole / custom. Drives which
    # adapter we load when starting the container and building the URL.
    type: Mapped[str] = mapped_column(String(50))

    # Where this provider came from: "builtin" (one of our YAML manifests)
    # or "custom" (user supplied image — locked off in MVP).
    source: Mapped[str] = mapped_column(String(50), default="builtin")

    # Container image incl. tag (e.g. "tsl0922/ttyd:1.7.4").
    image: Mapped[str] = mapped_column(String(500))

    # JSON blob — env overrides, command tweaks, ssh-proxy descriptor.
    # Kept as Text so this schema works on SQLite during dev too.
    config: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Port the process inside the container listens on. We never expose
    # host_port directly anymore — Traefik does the routing — so host_port
    # stays nullable for forward compatibility.
    internal_port: Mapped[int] = mapped_column(Integer, default=7681)
    host_port: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Template for the user-facing URL. The router substitutes {provider_id}
    # and {token} and returns the result via /terminal/session. Defaults to
    # the Traefik path layout — manifests can override per-provider.
    url_template: Mapped[str] = mapped_column(
        String(500),
        default="{scheme}://{host}/p/{provider_id}/?token={token}",
    )

    # Whether this provider needs the user's VM credentials brokered to the
    # container (e.g. Guacamole needs an SSH host/user/key per session).
    # ttyd local-shell mode = false.
    requires_ssh_proxy: Mapped[bool] = mapped_column(Boolean, default=False)

    # Only one provider per user can be "active" at a time — the drawer
    # uses the active one when the user opens a new session.
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

    # Lifecycle status reflected from docker: stopped | starting | running
    # | unhealthy | error. We never block the API on a docker round-trip —
    # status is updated by `start`/`stop` actions and the periodic poller.
    status: Mapped[str] = mapped_column(String(50), default="stopped")
    container_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_health_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc),
    )
