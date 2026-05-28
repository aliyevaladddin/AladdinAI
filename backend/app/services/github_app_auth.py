# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""GitHub App authentication helper.

Generates installation tokens for GitHub App bots to authenticate API requests.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

import httpx
import jwt

log = logging.getLogger(__name__)


async def get_installation_token(
    app_id: str,
    private_key_pem: str,
    installation_id: str,
) -> str:
    """Generate GitHub App installation token.

    Args:
        app_id: GitHub App ID
        private_key_pem: Private key in PEM format
        installation_id: Installation ID for the repository

    Returns:
        Installation access token valid for 1 hour

    Raises:
        ValueError: If installation_id is empty
        httpx.HTTPError: If token generation fails
    """
    if not app_id:
        raise ValueError("GitHub App ID is required and must be a non-empty string")
    if not private_key_pem:
        raise ValueError("Private key is required and must be a non-empty string")
    if not installation_id:
        raise ValueError("Installation ID is required and must be a non-empty string")

    # Generate JWT for GitHub App authentication
    now = int(time.time())
    payload = {
        "iat": now - 60,  # Issued 60 seconds in the past to account for clock drift
        "exp": now + (10 * 60),  # Expires in 10 minutes
        "iss": app_id,
    }

    jwt_token = jwt.encode(payload, private_key_pem, algorithm="RS256")

    # Exchange JWT for installation token
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        if "token" not in data:
            raise ValueError("Installation token not found in GitHub API response")

        log.info(f"Successfully generated GitHub App installation token for installation {installation_id}")
        return data["token"]


async def get_aladdinai_bot_token(installation_id: Optional[str] = None) -> str:
    """Get installation token for AladdinAI[bot].

    Args:
        installation_id: Optional installation ID, uses config default if not provided

    Returns:
        Installation access token
    """
    from app.config import settings

    return await get_installation_token(
        app_id=settings.aladdinai_bot_app_id,
        private_key_pem=settings.aladdinai_bot_private_key,
        installation_id=installation_id or settings.aladdinai_bot_installation_id,
    )


async def get_nvidia_bot_token(installation_id: Optional[str] = None) -> str:
    """Get installation token for NVIDIA Code Review[bot].

    Args:
        installation_id: Optional installation ID, uses config default if not provided

    Returns:
        Installation access token
    """
    from app.config import settings

    return await get_installation_token(
        app_id=settings.nvidia_bot_app_id,
        private_key_pem=settings.nvidia_bot_private_key,
        installation_id=installation_id or settings.nvidia_bot_installation_id,
    )
