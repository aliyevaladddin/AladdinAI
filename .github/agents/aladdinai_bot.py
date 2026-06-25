# NOTICE: This file is protected under RCF-PL
"""AladdinAI Bot - Autonomous AI agent living inside the GitHub repository.

An AI with personality that remembers every interaction, celebrates wins,
and reacts authentically to repository events.
"""
from __future__ import annotations

import logging
import random
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


# [RCF:PROTECTED]
class AladdinAIBot:
    """Active bot that reacts to all repository events."""

    name = "aladdinai-bot"
    description = "Active bot that reacts to all repository events"

# [RCF:PROTECTED]
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
        self.user_interactions: dict[str, int] = {}  # Track interaction count per user

# [RCF:PROTECTED]
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

            # Get personalized context
            user_context = await self._get_user_context(user, owner)

            # Assign bot to issue
            await self._assign_to_issue(owner, repo_name, issue_number, ["aliyevaladddin"])

            # Personalized welcome based on interaction history
            if "OWNER" in user_context:
                message = f"On it, boss! 🫡\n\nReviewing your issue now...\n\n*— AladdinAI Bot*"
            elif "FIRST interaction" in user_context:
                message = f"Welcome to AladdinAI, @{user}! 🎉\n\nThanks for opening your first issue! Our AI agents are reviewing it now...\n\n*— AladdinAI Bot*"
            elif "CORE contributor" in user_context:
                message = f"Always great to hear from you, @{user}! 🌟\n\nYour insights are invaluable. Our AI agents are on it!\n\n*— AladdinAI Bot*"
            elif "old friend" in user_context:
                message = f"Hey @{user}! Good to see you again 👋\n\nOur AI agents are reviewing your issue...\n\n*— AladdinAI Bot*"
            else:
                message = f"Thanks for opening this issue @{user}! 🙌\n\nOur AI agents are reviewing it now...\n\n*— AladdinAI Bot*"

            await self._post_issue_comment(owner, repo_name, issue_number, message)
            await self._react_to_issue(owner, repo_name, issue_number)

            # Milestone celebration
            if issue_number and issue_number % 10 == 0:
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
            user = comment.get("user", {}).get("login", "")

            if issue_number and ("@aladdinai-bot" in body.lower() or "@aladdinai" in body.lower()):
                # Get personalized context
                user_context = await self._get_user_context(user, owner)

                if "OWNER" in user_context:
                    message = f"👋 Yes, boss? What do you need?\n\n*— AladdinAI Bot*"
                elif "FIRST interaction" in user_context:
                    message = f"👋 Welcome @{user}! I'm here to help!\n\nI'm still learning, but feel free to ask questions about AladdinAI.\n\n*— AladdinAI Bot*"
                elif "CORE contributor" in user_context:
                    message = f"👋 @{user}! Always happy to help a core contributor.\n\nWhat can I do for you?\n\n*— AladdinAI Bot*"
                else:
                    message = f"👋 You called? I'm here to help!\n\nI'm still learning, but feel free to ask questions about AladdinAI.\n\n*— AladdinAI Bot*"

                await self._post_issue_comment(owner, repo_name, issue_number, message)

        # 🍴 Fork
        elif event_type == "fork":
            user = payload.get("forkee", {}).get("owner", {}).get("login", "")
            await self._notify_telegram(f"🍴 @{user} forked AladdinAI!")

        # 🔀 New PR
        elif event_type == "pull_request" and action == "opened":
            pr = payload.get("pull_request", {})
            pr_number = pr.get("number")
            user = pr.get("user", {}).get("login", "")

            # Get personalized context
            user_context = await self._get_user_context(user, owner)

            # Random roast
            roast = random.choice(ROASTS)

            # Personalized PR greeting
            if "OWNER" in user_context:
                greeting = f"Your PR is ready for review, boss! 🫡\n\nNVIDIA Code Review Bot will review shortly...\n\n_{roast}_"
            elif "FIRST interaction" in user_context:
                greeting = f"Welcome to AladdinAI, @{user}! 🎉 Your first PR — exciting!\n\nNVIDIA Code Review Bot will review shortly...\n\n_{roast}_"
            elif "CORE contributor" in user_context:
                greeting = f"@{user} bringing the heat again! 🔥\n\nNVIDIA Code Review Bot will review shortly...\n\n_{roast}_"
            elif "old friend" in user_context:
                greeting = f"Thanks for the PR @{user}! 🚀 Always good to see your contributions.\n\nNVIDIA Code Review Bot will review shortly...\n\n_{roast}_"
            else:
                greeting = f"Thanks for the PR @{user}! 🚀 NVIDIA Code Review Bot will review shortly...\n\n_{roast}_"

            if pr_number:
                await self._post_pr_comment(
                    owner,
                    repo_name,
                    pr_number,
                    f"{greeting}\n\n*— AladdinAI Bot*",
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

# [RCF:PROTECTED]
    async def _get_user_context(self, username: str, owner: str) -> str:
        """Get personalized context based on user interaction history.

        Args:
            username: GitHub username
            owner: Repository owner username

        Returns:
            Context string to add to bot personality prompt
        """
        # Defensive check for empty strings
        if not username or not owner:
            return "Regular user interaction."

        # Owner gets special treatment
        if username == owner:
            return "This is the OWNER of the repository. Show ultimate respect and loyalty."

        # Increment interaction count
        self.user_interactions[username] = self.user_interactions.get(username, 0) + 1
        interaction_count = self.user_interactions[username]

        if interaction_count == 1:
            return "This is their FIRST interaction with the repo. Be extra welcoming!"
        elif interaction_count > 50:
            return "This is a CORE contributor. Show deep respect and excitement."
        elif interaction_count > 10:
            return f"This is an old friend — they've interacted {interaction_count} times. Be familiar and warm."
        else:
            return f"They've interacted {interaction_count} times. Be friendly and encouraging."

# [RCF:PROTECTED]
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

# [RCF:PROTECTED]
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

# [RCF:PROTECTED]
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

# [RCF:PROTECTED]
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

# [RCF:PROTECTED]
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

# [RCF:PROTECTED]
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
