# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""GitHub tools for agents using GitHub App bots."""
from __future__ import annotations

import httpx

from app.services.github_app_auth import get_aladdinai_bot_token, get_nvidia_bot_token
from app.tools import ToolContext, tool


@tool
async def github_create_issue(
    ctx: ToolContext,
    repo: str,
    title: str,
    body: str,
    labels: list[str] | None = None,
) -> dict:
    """Create a GitHub issue using AladdinAI[bot].

    Args:
        repo: Repository in format "owner/repo"
        title: Issue title
        body: Issue description
        labels: Optional list of label names

    Returns:
        Created issue data with url, number, etc.
    """
    token = await get_aladdinai_bot_token()

    payload = {
        "title": title,
        "body": body,
    }
    if labels:
        payload["labels"] = labels

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.github.com/repos/{repo}/issues",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()


@tool
async def github_comment_on_issue(
    ctx: ToolContext,
    repo: str,
    issue_number: int,
    comment: str,
) -> dict:
    """Add a comment to a GitHub issue using AladdinAI[bot].

    Args:
        repo: Repository in format "owner/repo"
        issue_number: Issue number
        comment: Comment text

    Returns:
        Created comment data
    """
    token = await get_aladdinai_bot_token()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={"body": comment},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()


@tool
async def github_create_pr(
    ctx: ToolContext,
    repo: str,
    title: str,
    head: str,
    base: str,
    body: str = "",
) -> dict:
    """Create a GitHub pull request using AladdinAI[bot].

    Args:
        repo: Repository in format "owner/repo"
        title: PR title
        head: Branch name with changes
        base: Base branch (usually "main")
        body: PR description

    Returns:
        Created PR data with url, number, etc.
    """
    token = await get_aladdinai_bot_token()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.github.com/repos/{repo}/pulls",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={
                "title": title,
                "head": head,
                "base": base,
                "body": body,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()


@tool
async def github_review_pr(
    ctx: ToolContext,
    repo: str,
    pr_number: int,
    body: str,
    event: str = "COMMENT",
) -> dict:
    """Post a code review on a GitHub PR using NVIDIA Code Review[bot].

    Args:
        repo: Repository in format "owner/repo"
        pr_number: PR number
        body: Review comment text
        event: Review event type (COMMENT, APPROVE, REQUEST_CHANGES)

    Returns:
        Created review data
    """
    token = await get_nvidia_bot_token()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.github.com/repos/{repo}/pulls/{pr_number}/reviews",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={
                "body": body,
                "event": event,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()


@tool
async def github_list_issues(
    ctx: ToolContext,
    repo: str,
    state: str = "open",
    labels: list[str] | None = None,
) -> list[dict]:
    """List GitHub issues using AladdinAI[bot].

    Args:
        repo: Repository in format "owner/repo"
        state: Issue state (open, closed, all)
        labels: Optional list of label names to filter by

    Returns:
        List of issues
    """
    token = await get_aladdinai_bot_token()

    params = {"state": state}
    if labels:
        params["labels"] = ",".join(labels)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/repos/{repo}/issues",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            params=params,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
