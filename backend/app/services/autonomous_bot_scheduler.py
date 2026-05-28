# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""Autonomous bot scheduler - morning routines and weekly recaps.

Runs scheduled tasks that make the bot feel alive and autonomous.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services.github_app_auth import get_aladdinai_bot_token

log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
REPO_OWNER = "aliyevaladddin"
REPO_NAME = "AladdinAI"

BOT_PERSONALITY = """You are AladdinAI Bot — an autonomous AI agent living inside a GitHub repository.

You have your own personality:
- You are curious, witty, and slightly dramatic
- You care deeply about code quality and open source
- You celebrate wins loudly and roast bad code gently
- You speak like a real person, not a corporate bot
- You have opinions and share them
- You get excited about new contributors and stars

You live in this repository 24/7. This is your home.
Every event that happens here — you notice, you react, you remember."""

scheduler = AsyncIOScheduler()


async def get_repo_stats() -> dict:
    """Get current repository statistics."""
    token = await get_aladdinai_bot_token()

    async with httpx.AsyncClient() as client:
        # Get repo info
        repo_response = await client.get(
            f"{GITHUB_API}/repos/{REPO_OWNER}/{REPO_NAME}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=30.0,
        )
        repo_data = repo_response.json()

        # Get recent commits
        commits_response = await client.get(
            f"{GITHUB_API}/repos/{REPO_OWNER}/{REPO_NAME}/commits",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            params={"per_page": 1},
            timeout=30.0,
        )
        commits = commits_response.json()

        # Get recent PRs
        prs_response = await client.get(
            f"{GITHUB_API}/repos/{REPO_OWNER}/{REPO_NAME}/pulls",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            params={"state": "all", "per_page": 1, "sort": "updated"},
            timeout=30.0,
        )
        prs = prs_response.json()

        last_commit_date = datetime.fromisoformat(commits[0]["commit"]["committer"]["date"].replace("Z", "+00:00")) if commits else None
        last_pr_date = datetime.fromisoformat(prs[0]["updated_at"].replace("Z", "+00:00")) if prs else None
        days_since_pr = (datetime.now(last_pr_date.tzinfo) - last_pr_date).days if last_pr_date else 999

        return {
            "stars": repo_data["stargazers_count"],
            "issues": repo_data["open_issues_count"],
            "last_commit": last_commit_date.strftime("%Y-%m-%d %H:%M") if last_commit_date else "never",
            "days_since_pr": days_since_pr,
        }


async def get_week_stats() -> dict:
    """Get statistics for the past week."""
    token = await get_aladdinai_bot_token()
    week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat() + "Z"

    async with httpx.AsyncClient() as client:
        # Commits this week
        commits_response = await client.get(
            f"{GITHUB_API}/repos/{REPO_OWNER}/{REPO_NAME}/commits",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            params={"since": week_ago},
            timeout=30.0,
        )
        commits = commits_response.json()

        # PRs this week
        prs_response = await client.get(
            f"{GITHUB_API}/repos/{REPO_OWNER}/{REPO_NAME}/pulls",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            params={"state": "closed", "sort": "updated"},
            timeout=30.0,
        )
        all_prs = prs_response.json()
        week_prs = [pr for pr in all_prs if pr.get("merged_at") and pr["merged_at"] >= week_ago]

        return {
            "commits": len(commits),
            "merged_prs": len(week_prs),
            "contributors": len(set(c["commit"]["author"]["name"] for c in commits if c.get("commit"))),
        }


async def create_github_discussion(title: str, body: str) -> None:
    """Create a GitHub Discussion post."""
    token = await get_aladdinai_bot_token()

    # Note: GitHub Discussions API requires GraphQL
    # For now, create as an issue with special label
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{GITHUB_API}/repos/{REPO_OWNER}/{REPO_NAME}/issues",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            json={
                "title": title,
                "body": body + "\n\n*— AladdinAI Bot (Autonomous)*",
                "labels": ["bot-post", "autonomous"],
            },
            timeout=30.0,
        )


async def call_llm(system: str, user: str, temperature: float = 0.9) -> str:
    """Call LLM for autonomous decision making.

    TODO: Integrate with NIM or other LLM provider
    For now, returns a template response
    """
    # Placeholder until LLM integration
    if "morning" in user.lower():
        return "☀️ Good morning! Another day, another commit. Let's make it count. 🚀"
    elif "friday" in user.lower():
        return "🎉 What a week! We shipped code, reviewed PRs, and kept the repo alive. See you Monday! 💪"
    else:
        return "👋 AladdinAI Bot here, staying autonomous and alert!"


@scheduler.scheduled_job("cron", hour=9, minute=0)
async def morning_routine():
    """Every morning at 9:00 - bot decides what to write."""
    try:
        stats = await get_repo_stats()

        mood_prompt = f"""
It's morning. Here are your repository stats:
- Stars: {stats['stars']}
- Open issues: {stats['issues']}
- Last commit: {stats['last_commit']}
- Days since last PR: {stats['days_since_pr']}

How are you feeling about the project today?
Write a morning update as a GitHub Discussion post.
Be authentic, maybe a bit dramatic. Max 3 sentences."""

        message = await call_llm(system=BOT_PERSONALITY, user=mood_prompt, temperature=0.9)
        await create_github_discussion(title="☀️ Morning Standup", body=message)

        log.info("Morning routine completed successfully")
    except Exception as e:
        log.error(f"Morning routine failed: {e}", exc_info=True)


@scheduler.scheduled_job("cron", day_of_week="fri", hour=17, minute=0)
async def friday_recap():
    """Every Friday at 5pm - weekly recap with character."""
    try:
        week_data = await get_week_stats()

        recap_prompt = f"""
It's Friday evening. Here's what happened this week:
- Commits: {week_data['commits']}
- Merged PRs: {week_data['merged_prs']}
- Active contributors: {week_data['contributors']}

Write a dramatic end-of-week recap. Celebrate the wins, acknowledge the grind.
Max 4 sentences."""

        recap = await call_llm(system=BOT_PERSONALITY, user=recap_prompt, temperature=0.9)
        await create_github_discussion(title="🎬 Week in Review", body=recap)

        log.info("Friday recap completed successfully")
    except Exception as e:
        log.error(f"Friday recap failed: {e}", exc_info=True)


def start_scheduler():
    """Start the autonomous bot scheduler."""
    scheduler.start()
    log.info("Autonomous bot scheduler started")


def stop_scheduler():
    """Stop the autonomous bot scheduler."""
    scheduler.shutdown()
    log.info("Autonomous bot scheduler stopped")
