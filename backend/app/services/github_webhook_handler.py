# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""GitHub webhook event handler.

Processes incoming GitHub webhook events and triggers appropriate actions.
"""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


# [RCF:PROTECTED]
async def handle_github_event(event_type: str, payload: dict[str, Any]) -> None:
    """Handle incoming GitHub webhook events.

    Args:
        event_type: GitHub event type (e.g., 'pull_request', 'push', 'issues')
        payload: Event payload from GitHub
    """
    log.info(f"Processing GitHub event: {event_type}")

    # Run AladdinAI bot for all events
    try:
        import sys
        from pathlib import Path

        from app.config import settings
        from app.services.github_app_auth import get_aladdinai_bot_token

        # Add .github/agents to path for importing bots
        github_agents_path = Path(__file__).parent.parent.parent.parent / ".github" / "agents"
        sys.path.insert(0, str(github_agents_path))

        from aladdinai_bot import AladdinAIBot

        token = await get_aladdinai_bot_token()

        bot = AladdinAIBot(
            token=token,
            telegram_bot_token=getattr(settings, "telegram_bot_token", None),
            telegram_chat_id=getattr(settings, "telegram_chat_id", None),
        )

        await bot.run(event_type, payload)
    except Exception as e:
        log.error(f"Error running AladdinAI bot: {e}", exc_info=True)

    # Additional event-specific handlers
    handlers = {
        "pull_request": _handle_pull_request,
        "push": _handle_push,
        "issues": _handle_issues,
        "issue_comment": _handle_issue_comment,
    }

    handler = handlers.get(event_type)
    if handler:
        try:
            await handler(payload)
        except Exception as e:
            log.error(f"Error handling {event_type} event: {e}", exc_info=True)
    else:
        log.debug(f"No additional handler for event type: {event_type}")


# [RCF:PROTECTED]
async def _handle_pull_request(payload: dict[str, Any]) -> None:
    """Handle pull_request events.

    Triggers:
    - opened: Run code review agent
    - synchronize: Re-run code review on new commits
    - closed + merged: Cleanup tasks
    """
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {})

    pr_number = pr.get("number")
    repo_full_name = repo.get("full_name")

    log.info(f"PR #{pr_number} {action} in {repo_full_name}")

    if action in ("opened", "synchronize", "reopened"):
        # Code review is handled by GitHub Actions workflow
        # This webhook can trigger additional agent actions if needed
        log.info(f"PR #{pr_number} ready for review")

    elif action == "closed" and pr.get("merged"):
        log.info(f"PR #{pr_number} merged")
        # Could trigger post-merge actions here


# [RCF:PROTECTED]
async def _handle_push(payload: dict[str, Any]) -> None:
    """Handle push events.

    Triggers:
    - Push to main: Update changelog, run tests
    """
    ref = payload.get("ref", "")
    repo = payload.get("repository", {})
    commits = payload.get("commits", [])

    repo_full_name = repo.get("full_name")
    branch = ref.replace("refs/heads/", "")

    log.info(f"Push to {branch} in {repo_full_name}: {len(commits)} commits")

    if branch == "main":
        # Changelog workflow is handled by GitHub Actions
        log.info("Push to main branch detected")


# [RCF:PROTECTED]
async def _handle_issues(payload: dict[str, Any]) -> None:
    """Handle issues events.

    Triggers:
    - opened: Auto-label, assign to project
    - labeled: Trigger workflows based on labels
    """
    action = payload.get("action")
    issue = payload.get("issue", {})
    repo = payload.get("repository", {})

    issue_number = issue.get("number")
    repo_full_name = repo.get("full_name")

    log.info(f"Issue #{issue_number} {action} in {repo_full_name}")

    if action == "opened":
        # Could auto-label or assign issues here
        log.info(f"New issue #{issue_number} opened")


# [RCF:PROTECTED]
async def _handle_issue_comment(payload: dict[str, Any]) -> None:
    """Handle issue_comment events.

    Triggers:
    - created: Check for bot commands in comments
    """
    action = payload.get("action")
    comment = payload.get("comment", {})
    issue = payload.get("issue", {})

    if action == "created":
        body = comment.get("body", "")
        issue_number = issue.get("number")

        # Check for bot commands (e.g., "@AladdinAI review this")
        if "@AladdinAI" in body or "@aladdinai" in body.lower():
            log.info(f"Bot mentioned in issue #{issue_number}")
            # Could trigger agent response here
