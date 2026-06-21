"""Tests for app.config secret-strength enforcement.

The guard must FAIL CLOSED: a production-looking deployment that still carries
placeholder `change-me` secrets has to refuse to boot, while a local dev box
(SQLite, no explicit env) keeps booting with a warning.
"""
import pytest

from app.config import Settings, _is_dev_mode


# ── _is_dev_mode inference ───────────────────────────────────────────────

def test_dev_mode_explicit_prod(monkeypatch):
    monkeypatch.setenv("ALADDIN_ENV", "production")
    assert _is_dev_mode("sqlite+aiosqlite:///./x.db") is False


def test_dev_mode_explicit_dev(monkeypatch):
    monkeypatch.setenv("ALADDIN_ENV", "dev")
    assert _is_dev_mode("postgresql+asyncpg://u:p@h/db") is True


def test_dev_mode_inferred_sqlite_is_dev(monkeypatch):
    monkeypatch.delenv("ALADDIN_ENV", raising=False)
    assert _is_dev_mode("sqlite+aiosqlite:///./x.db") is True


def test_dev_mode_inferred_postgres_is_prod(monkeypatch):
    # Unset env + non-SQLite DB → treated as production (fail closed).
    monkeypatch.delenv("ALADDIN_ENV", raising=False)
    assert _is_dev_mode("postgresql+asyncpg://u:p@h/db") is False


# ── boot-time enforcement ────────────────────────────────────────────────

def test_insecure_jwt_secret_rejected_in_prod(monkeypatch):
    monkeypatch.delenv("ALADDIN_ENV", raising=False)
    with pytest.raises(ValueError, match="JWT_SECRET"):
        Settings(
            database_url="postgresql+asyncpg://u:p@h/db",
            jwt_secret="change-me-in-production",
            terminal_token_secret="a-strong-terminal-secret",
        )


def test_insecure_terminal_secret_rejected_in_prod(monkeypatch):
    monkeypatch.setenv("ALADDIN_ENV", "production")
    with pytest.raises(ValueError, match="TERMINAL_TOKEN_SECRET"):
        Settings(
            jwt_secret="a-strong-jwt-secret-value",
            terminal_token_secret="change-me-terminal-token-secret",
        )


def test_insecure_defaults_allowed_in_dev(monkeypatch):
    monkeypatch.delenv("ALADDIN_ENV", raising=False)
    s = Settings(
        database_url="sqlite+aiosqlite:///./x.db",
        jwt_secret="change-me-in-production",
        terminal_token_secret="change-me-terminal-token-secret",
    )
    assert s.jwt_secret == "change-me-in-production"


def test_strong_secrets_boot_in_prod(monkeypatch):
    monkeypatch.setenv("ALADDIN_ENV", "production")
    s = Settings(
        jwt_secret="a" * 32,
        terminal_token_secret="b" * 32,
    )
    assert s.terminal_token_secret == "b" * 32
