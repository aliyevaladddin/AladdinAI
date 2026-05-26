# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""
Pydantic schema for terminal provider manifests.

Validates the structure of YAML manifests in app/terminal_plugins/*.yaml
before they're used to start containers.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class HealthcheckManifest(BaseModel):
    """Docker healthcheck configuration."""
    test: List[str] = Field(..., description="Healthcheck command (e.g. ['CMD', 'wget', ...])")
    interval: Optional[str] = Field(None, description="Check interval (e.g. '30s')")
    timeout: Optional[str] = Field(None, description="Timeout per check (e.g. '5s')")
    retries: Optional[int] = Field(None, description="Number of retries before unhealthy")
    start_period: Optional[str] = Field(None, description="Grace period before first check (e.g. '5s')")

    @field_validator("test")
    @classmethod
    def validate_test_command(cls, v: List[str]) -> List[str]:
        if not v or len(v) < 2:
            raise ValueError("healthcheck test must have at least 2 elements (e.g. ['CMD', 'wget', ...])")
        if v[0] not in ("CMD", "CMD-SHELL"):
            raise ValueError("healthcheck test must start with 'CMD' or 'CMD-SHELL'")
        return v


class TerminalManifest(BaseModel):
    """
    Schema for terminal provider manifests (ttyd.yaml, wetty.yaml, etc.).

    Each manifest describes how to start a terminal provider container:
    - Docker image to use
    - Command and environment variables
    - Internal port the provider listens on
    - Whether it requires SSH proxy (VM credentials)
    - URL template for session URLs
    """

    type: str = Field(..., description="Provider type identifier (e.g. 'ttyd', 'wetty')")
    name: str = Field(..., description="Human-readable name shown in UI")
    description: Optional[str] = Field(None, description="Markdown description for marketplace")

    image: str = Field(..., description="Docker image (e.g. 'tsl0922/ttyd:1.7.4')")
    internal_port: int = Field(..., ge=1, le=65535, description="Port the container listens on")

    command: Optional[List[str]] = Field(None, description="Container entrypoint command")
    env: Optional[Dict[str, str]] = Field(default_factory=dict, description="Environment variables")

    # Volume mounts: host_path:container_path or host_path:container_path:ro
    volumes: Optional[List[str]] = Field(default_factory=list, description="Volume mounts")

    healthcheck: Optional[HealthcheckManifest] = Field(None, description="Docker healthcheck config")

    requires_ssh_proxy: bool = Field(
        default=False,
        description="Whether this provider needs VM credentials (SSH/RDP)",
    )

    strip_prefix: bool = Field(
        default=True,
        description="Whether Traefik should strip /p/{provider_id} prefix before proxying",
    )

    url_template: str = Field(
        default="{scheme}://{host}/p/{provider_id}/?token={token}",
        description="Template for session URLs (supports {scheme}, {host}, {provider_id}, {token})",
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if not v or not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("type must be alphanumeric (with - or _)")
        return v

    @field_validator("url_template")
    @classmethod
    def validate_url_template(cls, v: str) -> str:
        required_vars = {"{provider_id}", "{token}"}
        missing = required_vars - set(v.split())
        if missing:
            # More lenient check: just verify the string contains the substrings
            for var in required_vars:
                if var not in v:
                    raise ValueError(f"url_template must contain {var}")
        return v

    class Config:
        extra = "forbid"  # Reject unknown fields to catch typos in manifests
