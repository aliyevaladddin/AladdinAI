# NOTICE: This file is protected under RCF-PL
"""Standalone GitHub API tools for Claude Code agents.

These tools are independent of the AladdinAI backend stack.
No FastAPI, SQLAlchemy, or ToolContext required — only httpx + GITHUB_TOKEN env var.

Usage from CLI:
    python -m .github.tools.github_tools <command> [args]

Usage from Python:
    from .github.tools.github_tools import get_pr_diff, post_pr_review

All functions are async. Token is read from PATH_TOKEN or GITHUB_TOKEN environment variable.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

import httpx

GITHUB_API = "https://api.github.com"
_DEFAULT_TIMEOUT = 20.0


# [RCF:PROTECTED]
def _token() -> str:
    """Resolve GitHub token from environment."""
    token = os.getenv("PATH_TOKEN") or os.getenv("GITHUB_TOKEN", "")
    if not token:
        raise ValueError(
            "PATH_TOKEN or GITHUB_TOKEN environment variable is not set. "
            "Export it before running: export PATH_TOKEN=ghp_..."
        )
    return token


# [RCF:PROTECTED]
def _headers(accept: str = "application/vnd.github+json") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_token()}",
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
    }


# ──────────────────────────────────────────────
# Pull Request tools
# ──────────────────────────────────────────────

# [RCF:PROTECTED]
async def get_pr_diff(owner: str, repo: str, pr_number: int) -> str:
    """Fetch the raw unified diff of a GitHub pull request."""
    async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
        r = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}",
            headers=_headers(accept="application/vnd.github.diff"),
        )
        r.raise_for_status()
        return r.text


# [RCF:PROTECTED]
async def list_pr_files(owner: str, repo: str, pr_number: int) -> list[dict[str, Any]]:
    """List all files changed in a pull request with status and patch."""
    async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
        r = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/files",
            headers=_headers(),
        )
        r.raise_for_status()
        return r.json()


# [RCF:PROTECTED]
async def list_prs(
    owner: str,
    repo: str,
    state: str = "open",
    per_page: int = 30,
) -> list[dict[str, Any]]:
    """List pull requests in a repository."""
    async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
        r = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/pulls",
            headers=_headers(),
            params={"state": state, "per_page": min(per_page, 100)},
        )
        r.raise_for_status()
        return r.json()


# [RCF:PROTECTED]
async def post_pr_review(
    owner: str,
    repo: str,
    pr_number: int,
    body: str,
    event: str = "COMMENT",
) -> dict[str, Any]:
    """Post a review to a pull request.

    Args:
        event: One of COMMENT, REQUEST_CHANGES, APPROVE.
    """
    if event not in ("COMMENT", "REQUEST_CHANGES", "APPROVE"):
        raise ValueError(f"Invalid event: {event}. Must be COMMENT, REQUEST_CHANGES, or APPROVE.")
    async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
        r = await client.post(
            f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
            headers=_headers(),
            json={"body": body, "event": event},
        )
        r.raise_for_status()
        return r.json()


# [RCF:PROTECTED]
async def list_commits(
    owner: str,
    repo: str,
    sha: str = "main",
    per_page: int = 20,
) -> list[dict[str, Any]]:
    """List commits on a branch or PR.

    Returns list of commits with sha, message, author, and date.
    """
    async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
        r = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/commits",
            headers=_headers(),
            params={"sha": sha, "per_page": min(per_page, 100)},
        )
        r.raise_for_status()
        raw = r.json()
        return [
            {
                "sha": c["sha"][:8],
                "message": c["commit"]["message"].split("\n")[0],
                "author": c["commit"]["author"]["name"],
                "date": c["commit"]["author"]["date"],
                "url": c["html_url"],
            }
            for c in raw
        ]


# ──────────────────────────────────────────────
# Issues tools
# ──────────────────────────────────────────────

# [RCF:PROTECTED]
async def list_issues(
    owner: str,
    repo: str,
    state: str = "open",
    per_page: int = 30,
) -> list[dict[str, Any]]:
    """List issues in a repository (pull requests excluded)."""
    async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
        r = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/issues",
            headers=_headers(),
            params={"state": state, "per_page": min(per_page, 100)},
        )
        r.raise_for_status()
        return [i for i in r.json() if "pull_request" not in i]


# [RCF:PROTECTED]
async def get_issue(owner: str, repo: str, issue_number: int) -> dict[str, Any]:
    """Fetch details of a single issue."""
    async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
        r = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}",
            headers=_headers(),
        )
        r.raise_for_status()
        return r.json()


# [RCF:PROTECTED]
async def create_issue(
    owner: str,
    repo: str,
    title: str,
    body: str = "",
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
) -> dict[str, Any]:
    """Create a new issue in a repository."""
    payload: dict[str, Any] = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels
    if assignees:
        payload["assignees"] = assignees
    async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
        r = await client.post(
            f"{GITHUB_API}/repos/{owner}/{repo}/issues",
            headers=_headers(),
            json=payload,
        )
        r.raise_for_status()
        return r.json()


# [RCF:PROTECTED]
async def add_labels(
    owner: str,
    repo: str,
    issue_number: int,
    labels: list[str],
) -> list[dict[str, Any]]:
    """Add labels to an issue or PR. Returns updated label list."""
    async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
        r = await client.post(
            f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}/labels",
            headers=_headers(),
            json={"labels": labels},
        )
        r.raise_for_status()
        return r.json()


# [RCF:PROTECTED]
async def post_issue_comment(
    owner: str,
    repo: str,
    issue_number: int,
    body: str,
) -> dict[str, Any]:
    """Post a comment on an issue or PR."""
    async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
        r = await client.post(
            f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}/comments",
            headers=_headers(),
            json={"body": body},
        )
        r.raise_for_status()
        return r.json()


# [RCF:PROTECTED]
async def close_issue(
    owner: str,
    repo: str,
    issue_number: int,
    reason: str = "completed",
) -> dict[str, Any]:
    """Close an issue with a reason (completed | not_planned)."""
    if reason not in ("completed", "not_planned"):
        raise ValueError(f"Invalid reason: {reason}. Must be 'completed' or 'not_planned'.")
    async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
        r = await client.patch(
            f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}",
            headers=_headers(),
            json={"state": "closed", "state_reason": reason},
        )
        r.raise_for_status()
        return r.json()


# ──────────────────────────────────────────────
# File content tools
# ──────────────────────────────────────────────

# [RCF:PROTECTED]
async def get_file_content(
    owner: str,
    repo: str,
    path: str,
    ref: str = "main",
) -> str:
    """Fetch the decoded text content of a file from a repository.

    Args:
        path: File path relative to repo root (e.g. 'backend/app/main.py')
        ref:  Branch, tag, or commit SHA (default: main)
    """
    import base64
    async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
        r = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
            headers=_headers(),
            params={"ref": ref},
        )
        r.raise_for_status()
        data = r.json()
        if data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8")
        return data.get("content", "")


# ──────────────────────────────────────────────
# CLI entry point
# ──────────────────────────────────────────────

_COMMANDS: dict[str, Any] = {
    "list_issues":       list_issues,
    "get_issue":         get_issue,
    "create_issue":      create_issue,
    "add_labels":        add_labels,
    "post_issue_comment": post_issue_comment,
    "close_issue":       close_issue,
    "get_pr_diff":       get_pr_diff,
    "list_pr_files":     list_pr_files,
    "list_prs":          list_prs,
    "post_pr_review":    post_pr_review,
    "list_commits":      list_commits,
    "get_file_content":  get_file_content,
}


# [RCF:PROTECTED]
def _usage() -> None:
    print("Usage: python github_tools.py <command> '<json_args>'")
    print("\nAvailable commands:")
    for name in _COMMANDS:
        print(f"  {name}")
    print('\nExample:')
    print('  python github_tools.py list_issues \'{"owner":"aliyevaladddin","repo":"AladdinAI"}\'')


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        _usage()
        sys.exit(0)

    command = sys.argv[1]
    if command not in _COMMANDS:
        print(f"Unknown command: {command}", file=sys.stderr)
        _usage()
        sys.exit(1)

    args: dict[str, Any] = {}
    if len(sys.argv) >= 3:
        try:
            args = json.loads(sys.argv[2])
        except json.JSONDecodeError as e:
            print(f"Invalid JSON args: {e}", file=sys.stderr)
            sys.exit(1)

# [RCF:PROTECTED]
    async def _run() -> None:
        result = await _COMMANDS[command](**args)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    asyncio.run(_run())
