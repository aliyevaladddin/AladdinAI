"""AladdinAI Bot - Active GitHub bot that reacts to repository events.

Responds to stars, forks, issues, PRs, pushes, and watches with reactions
and Telegram notifications.
"""
from __future__ import annotations

import logging
import random
from typing import Any

import httpx

log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
REACTIONS = ["+1", "rocket", "heart", "hooray", "eyes"]


class AladdinAIBot:
    """Active bot that reacts to all repository events."""

    name = "aladdinai-bot"
    description = "Active bot that reacts to all repository events"

    def __init__(self, token: str, telegram_bot_token: str | None = None, telegram_chat_id: str | None = None):
        """Initialize AladdinAI bot.

        Args:
            token: GitHub App installation token
            telegram_bot_token: Optional Telegram bot token for notifications
            telegram_chat_id: Optional Telegram chat ID for notifications
        """
        self.token = token
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id

    async def run(self, event_type: str, payload: dict[str, Any]) -> None:
        """Process GitHub webhook event.

        Args:
            event_type: GitHub event type (star, issues, pull_request, etc.)
            payload: GitHub webhook payload
        """
        action = payload.get("action")
        repo = payload.get("repository", {})
        owner = repo.get("owner", {}).get("login", "")
        repo_name = repo.get("name", "")

        # ⭐ Star event
        if event_type == "star" and action == "created":
            user = payload.get("sender", {}).get("login", "")
            stars = repo.get("stargazers_count", 0)
            await self._notify_telegram(f"⭐ @{user} starred AladdinAI! Total: {stars} stars")

        # 🐛 New issue
        elif event_type == "issues" and action == "opened":
            issue = payload.get("issue", {})
            issue_number = issue.get("number")
            user = issue.get("user", {}).get("login", "")
            await self._post_issue_comment(
                owner,
                repo_name,
                issue_number,
                f"Thanks for opening this issue @{user}! 🙌\n\n"
                f"Our AI agents are reviewing it now...\n\n"
                f"*— AladdinAI Bot*",
            )
            await self._react_to_issue(owner, repo_name, issue_number)

        # 🍴 Fork
        elif event_type == "fork":
            user = payload.get("forkee", {}).get("owner", {}).get("login", "")
            await self._notify_telegram(f"🍴 @{user} forked AladdinAI!")

        # 🔀 New PR
        elif event_type == "pull_request" and action == "opened":
            pr = payload.get("pull_request", {})
            pr_number = pr.get("number")
            user = pr.get("user", {}).get("login", "")
            await self._post_pr_comment(
                owner,
                repo_name,
                pr_number,
                f"Thanks for the PR @{user}! 🚀 NVIDIA Code Review Bot will review shortly...\n\n"
                f"*— AladdinAI Bot*",
            )
            await self._react_to_issue(owner, repo_name, pr_number)

        # 🚀 Push
        elif event_type == "push":
            commits = payload.get("commits", [])
            if commits:
                summary = "\n".join([f"• {c.get('message', '')}" for c in commits[:5]])
                await self._notify_telegram(f"🚀 New push to AladdinAI:\n{summary}")

        # 👀 Watch
        elif event_type == "watch" and action == "started":
            user = payload.get("sender", {}).get("login", "")
            await self._notify_telegram(f"👀 @{user} is now watching AladdinAI!")

    async def _post_issue_comment(self, owner: str, repo: str, issue_number: int, body: str) -> None:
        """Post a comment on an issue."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}/comments",
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    json={"body": body},
                    timeout=30.0,
                )
                response.raise_for_status()
        except httpx.HTTPError as e:
            log.error(f"Failed to post comment on issue #{issue_number}: {e}")

    async def _post_pr_comment(self, owner: str, repo: str, pr_number: int, body: str) -> None:
        """Post a comment on a pull request."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments",
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    json={"body": body},
                    timeout=30.0,
                )
                response.raise_for_status()
        except httpx.HTTPError as e:
            log.error(f"Failed to post comment on PR #{pr_number}: {e}")

    async def _react_to_issue(self, owner: str, repo: str, issue_number: int) -> None:
        """Add a random reaction to an issue or PR."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}/reactions",
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    json={"content": random.choice(REACTIONS)},
                    timeout=30.0,
                )
                response.raise_for_status()
        except httpx.HTTPError as e:
            log.error(f"Failed to add reaction to issue #{issue_number}: {e}")

    async def _notify_telegram(self, message: str) -> None:
        """Send notification to Telegram."""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            return

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage",
                    json={"chat_id": self.telegram_chat_id, "text": message},
                    timeout=30.0,
                )
                response.raise_for_status()
        except httpx.HTTPError as e:
            log.error(f"Failed to send Telegram notification: {e}")
