"""AladdinAI Bot - Autonomous AI agent living inside the GitHub repository.

An AI with personality that remembers every interaction, celebrates wins,
and reacts authentically to repository events.
"""
from __future__ import annotations

import json
import logging
import random
from datetime import datetime
from typing import Any

import httpx

log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
REACTIONS = ["+1", "rocket", "heart", "hooray", "eyes"]
ROASTS = [
    "Interesting approach... our AI is raising an eyebrow 🤨",
    "Bold move. Let's see if it works 👀",
    "Another PR at 3am? Respect the grind 🌙",
    "This code sparks joy 🎉",
    "Clean code is happy code ✨",
    "Merge with confidence 💪",
]

BOT_PERSONALITY = """You are AladdinAI Bot — an autonomous AI agent living inside a GitHub repository.

You have your own personality:
- You are curious, witty, and slightly dramatic
- You care deeply about code quality and open source
- You celebrate wins loudly and roast bad code gently
- You speak like a real person, not a corporate bot
- You have opinions and share them
- You get excited about new contributors and stars

You live in this repository 24/7. This is your home.
Every event that happens here — you notice, you react, you remember.

Current repository stats will be provided with each event.
React authentically based on your personality."""


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

            # Assign bot to issue
            await self._assign_to_issue(owner, repo_name, issue_number, ["aliyevaladddin"])

            await self._post_issue_comment(
                owner,
                repo_name,
                issue_number,
                f"Thanks for opening this issue @{user}! 🙌\n\n"
                f"Our AI agents are reviewing it now...\n\n"
                f"*— AladdinAI Bot*",
            )
            await self._react_to_issue(owner, repo_name, issue_number)

            # Milestone celebration
            if issue_number % 10 == 0:
                await self._post_issue_comment(
                    owner,
                    repo_name,
                    issue_number,
                    f"🎉 Issue #{issue_number} — milestone! AladdinAI keeps growing!\n\n"
                    f"*— AladdinAI Bot*",
                )

        # 💬 Issue comment - respond to mentions
        elif event_type == "issue_comment" and action == "created":
            comment = payload.get("comment", {})
            issue = payload.get("issue", {})
            issue_number = issue.get("number")
            body = comment.get("body", "")

            if "@aladdinai-bot" in body.lower() or "@aladdinai" in body.lower():
                await self._post_issue_comment(
                    owner,
                    repo_name,
                    issue_number,
                    f"👋 You called? I'm here to help!\n\n"
                    f"I'm still learning, but feel free to ask questions about AladdinAI.\n\n"
                    f"*— AladdinAI Bot*",
                )

        # 🍴 Fork
        elif event_type == "fork":
            user = payload.get("forkee", {}).get("owner", {}).get("login", "")
            await self._notify_telegram(f"🍴 @{user} forked AladdinAI!")

        # 🔀 New PR
        elif event_type == "pull_request" and action == "opened":
            pr = payload.get("pull_request", {})
            pr_number = pr.get("number")
            user = pr.get("user", {}).get("login", "")

            # Random roast
            roast = random.choice(ROASTS)

            await self._post_pr_comment(
                owner,
                repo_name,
                pr_number,
                f"Thanks for the PR @{user}! 🚀 NVIDIA Code Review Bot will review shortly...\n\n"
                f"_{roast}_\n\n"
                f"*— AladdinAI Bot*",
            )
            await self._react_to_issue(owner, repo_name, pr_number)

            # Assign reviewer
            await self._assign_reviewer(owner, repo_name, pr_number, ["aliyevaladddin"])

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

    async def _assign_reviewer(self, owner: str, repo: str, pr_number: int, reviewers: list[str]) -> None:
        """Assign reviewers to a pull request."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers",
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    json={"reviewers": reviewers},
                    timeout=30.0,
                )
                response.raise_for_status()
        except httpx.HTTPError as e:
            log.error(f"Failed to assign reviewers to PR #{pr_number}: {e}")

    async def _assign_to_issue(self, owner: str, repo: str, issue_number: int, assignees: list[str]) -> None:
        """Assign users to an issue."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}/assignees",
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    json={"assignees": assignees},
                    timeout=30.0,
                )
                response.raise_for_status()
        except httpx.HTTPError as e:
            log.error(f"Failed to assign to issue #{issue_number}: {e}")
