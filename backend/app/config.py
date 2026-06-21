# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
import logging
import os
from typing import List

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings

_log = logging.getLogger(__name__)

# Placeholder secrets shipped in .env.example. Booting with any of these in a
# production context is refused outright (see `_is_dev_mode`).
_INSECURE_DEFAULTS = {
    "",
    "change-me-in-production",
    "change-me-terminal-token-secret",
    "secret",
    "changeme",
}


def _is_dev_mode(database_url: str | None) -> bool:
    """Decide whether insecure placeholder secrets are tolerable.

    Fail closed: only an explicit local-dev signal unlocks the insecure
    defaults. An unset `ALADDIN_ENV` is inferred from the database — a SQLite
    URL is a local dev box, anything else (e.g. Postgres) is treated as
    production so a deploy that forgets to set `ALADDIN_ENV` still refuses to
    boot rather than silently running on `change-me` secrets.
    """
    env = os.getenv("ALADDIN_ENV", "").strip().lower()
    if env in ("prod", "production", "staging"):
        return False
    if env in ("dev", "development", "local", "test"):
        return True
    # ALADDIN_ENV unset → infer from the database backend.
    return (database_url or "").startswith("sqlite")


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./aladdinai.db"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    fernet_key: str = ""  # Set in .env — generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

    # ── CORS ─────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins for the frontend.
    # Example in .env:  CORS_ORIGINS=https://app.example.com,https://admin.example.com
    # Defaults to localhost for local development.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        """Return cors_origins as a parsed list of stripped, non-empty URLs."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @field_validator("database_url", mode="before")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @model_validator(mode="after")
    def _enforce_secret_strength(self) -> "Settings":
        """Refuse to boot with placeholder secrets outside local dev.

        Covers every HMAC/signing secret at once so adding a new one can't
        quietly skip the check. Fails closed: a production-looking deployment
        (non-SQLite DB, no explicit dev `ALADDIN_ENV`) with any `change-me`
        secret raises instead of running insecurely.
        """
        is_dev = _is_dev_mode(self.database_url)
        # (field name, env var, generation hint)
        guarded = [
            ("jwt_secret", "JWT_SECRET", "openssl rand -hex 32"),
            ("terminal_token_secret", "TERMINAL_TOKEN_SECRET", "openssl rand -hex 32"),
        ]
        for attr, env_name, hint in guarded:
            value = getattr(self, attr)
            if value not in _INSECURE_DEFAULTS:
                continue
            if not is_dev:
                raise ValueError(
                    f"{env_name} is set to an insecure default value. "
                    f"Generate a strong secret with: {hint}"
                )
            _log.warning(
                "⚠️  %s is using an insecure default — safe for local dev only. "
                "Set %s in .env before deploying to production.",
                env_name, env_name,
            )
        return self

    @field_validator("fernet_key", mode="before")
    @classmethod
    def validate_fernet_key(cls, v: str) -> str:
        if not v or not v.strip():
            _log.warning(
                "⚠️  FERNET_KEY is not set — API keys stored by providers will NOT be "
                "encrypted at rest. Generate a key with: "
                "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        return v

    # ── Open-core edition ────────────────────────────────────────────
    # "community" = public self-hosted image: the Self-Forging trace-capture
    # is OFF by default (a community user has no reason to carry commercial
    # instrumentation). "internal"/"cloud" = our own infra: capture ON by
    # default. A per-agent `tracing.enabled` flag always overrides this, and
    # the TRACING_DISABLED env var is a global kill-switch on top of both.
    # Env var: ALADDIN_EDITION (explicit alias — the field name `edition` would
    # otherwise match the env var `EDITION`, which is too generic).
    edition: str = Field(default="community", validation_alias="ALADDIN_EDITION")

    # ── Terminal provider runtime ────────────────────────────────────
    # Remote Docker daemon over TLS (per user's deployment choice).
    # Leave docker_remote_url empty in dev to fall back to the local
    # daemon at unix:///var/run/docker.sock — provider features will be
    # disabled unless docker_remote_url is set in production.
    docker_remote_url: str = ""          # e.g. "tcp://docker.example.com:2376"
    docker_tls_cert_path: str = ""        # client cert.pem
    docker_tls_key_path: str = ""         # client key.pem
    docker_tls_ca_path: str = ""          # CA ca.pem
    docker_tls_verify: bool = True

    # The user-facing host name in front of Traefik. All per-user
    # provider containers share this host and are disambiguated by a
    # path prefix that Traefik routes to the matching container.
    # Example:  terminal_public_host = "terminal.aladdin.local"
    #           url -> https://terminal.aladdin.local/p/<provider_id>/?token=…
    terminal_public_host: str = "localhost:8086"
    terminal_public_scheme: str = "http"
    terminal_traefik_entrypoint: str = "web"   # web | websecure
    terminal_traefik_network: str = "aladdin_terminal"
    terminal_traefik_router_priority: int = 100
    # When the docker network already exists on the remote host, we just
    # attach to it. We never auto-create networks — that's an infra task.

    # HMAC secret for one-time terminal session tokens. MUST be set in
    # production; defaults are unusable for cross-process verification
    # but won't crash a dev session.
    terminal_token_secret: str = "change-me-terminal-token-secret"
    terminal_token_ttl_seconds: int = 3600  # 1 hour — multi-use token, lives as long as the session
    # Longer-lived cookie issued by forward-auth after the entry token is
    # consumed; covers all sub-resource fetches the iframe makes (CSS, JS,
    # WS upgrade). Keep this comfortably above a typical idle session length
    # but short enough that a leaked cookie has a bounded blast radius.
    terminal_session_ttl_seconds: int = 60 * 60   # 1 hour
    # Cookie name set on `terminal_public_host`. Picked to avoid colliding
    # with anything the provider container itself might set.
    terminal_session_cookie_name: str = "aladdin_term_sess"

    # Directory where the backend writes per-provider Traefik routing configs.
    # Traefik mounts this directory read-only and hot-reloads on change.
    # In docker-compose this is the shared ./traefik-dynamic volume.
    traefik_dynamic_config_dir: str = "/traefik-dynamic"

    # ── GitHub App Bots ──────────────────────────────────────────────
    github_webhook_secret: str = ""

    # AladdinAI[bot] - general purpose automation
    aladdinai_bot_app_id: str = ""
    aladdinai_bot_private_key: str = ""  # PEM format private key
    aladdinai_bot_installation_id: str = ""

    # NVIDIA Code Review[bot] - automated code reviews
    nvidia_bot_app_id: str = ""
    nvidia_bot_private_key: str = ""  # PEM format private key
    nvidia_bot_installation_id: str = ""

    # ── Telegram Notifications ───────────────────────────────────────
    telegram_bot_token: str = ""  # Optional: for AladdinAI bot notifications
    telegram_chat_id: str = ""  # Optional: chat ID for notifications

    model_config = {"env_file": "../.env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
