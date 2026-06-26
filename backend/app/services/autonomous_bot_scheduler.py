# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""Autonomous bot scheduler - morning routines and weekly recaps.

Runs scheduled tasks that make the bot feel alive and autonomous.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.database import async_session
from app.models.user import User
from app.models.activity import Activity
from app.models.deal import Deal
from app.models.email_account import EmailAccount
from app.models.llm_provider import LLMProvider
from app.services.github_app_auth import get_aladdinai_bot_token
from app.services.llm_service import resolve_llm_provider, chat_completion
from app.config import settings

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


# [RCF:PROTECTED]
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


# [RCF:PROTECTED]
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


# [RCF:PROTECTED]
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


# [RCF:PROTECTED]
async def _get_first_user_id() -> int:
    async with async_session() as db:
        user = (await db.execute(select(User).order_by(User.id))).scalars().first()
        if not user:
            raise ValueError("No user found in database")
        return user.id


# [RCF:PROTECTED]
async def call_llm(system: str, user: str, temperature: float = 0.9, user_id: int | None = None) -> str:
    """Call LLM for autonomous decision making using the configured LLMProvider."""
    if user_id is None:
        try:
            user_id = await _get_first_user_id()
        except Exception as e:
            log.error(f"Failed to get first user ID for LLM: {e}")
            return "Error: No user configured."

    async with async_session() as db:
        try:
            # Try to get the user's first agent's configuration
            from app.models.agent import Agent
            agent_res = await db.execute(
                select(Agent)
                .where(Agent.user_id == user_id)
                .order_by(Agent.id)
            )
            agents = agent_res.scalars().all()

            provider = None
            model = None

            for agent in agents:
                p_res = await db.execute(
                    select(LLMProvider).where(
                        LLMProvider.id == agent.llm_provider_id,
                        LLMProvider.status == "connected"
                    )
                )
                p = p_res.scalars().first()
                if p:
                    provider = p
                    model = agent.model
                    break

            if not provider:
                provider = await resolve_llm_provider(db, user_id)
                import json as _json
                models = []
                if provider.models_available:
                    try:
                        models = _json.loads(provider.models_available)
                    except Exception:
                        pass
                # Filter out models that look like embedding / safety models
                models = [
                    m for m in models 
                    if isinstance(m, str) and m.strip() and not any(x in m.lower() for x in ["embed", "parse", "pii", "detector", "safety", "reward", "guard"])
                ]
                model = models[0] if models else "meta/llama-3.1-405b-instruct"

            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ]

            res = await chat_completion(provider, model, messages)
            return res.get("content") or ""
        except Exception as e:
            log.exception(f"LLM call failed: {e}")
            # Fallback values for basic system messages when provider is offline
            if "morning" in user.lower():
                return "☀️ Good morning! Another day, another commit. Let's make it count. 🚀"
            elif "friday" in user.lower():
                return "🎉 What a week! We shipped code, reviewed PRs, and kept the repo alive. See you Monday! 💪"
            return "👋 AladdinAI Bot here, staying autonomous and alert!"


# [RCF:PROTECTED]
async def send_user_daily_digest(db: AsyncSession, user: User) -> None:
    """Generate and send daily digest of CRM activities, deals, and tasks to the user.

    After data processing, send to Telegram bot Aladdin Aliyev (после обработки данных отправить в телеграм бот Aladdin Aliyev).
    """
    now = datetime.now(timezone.utc)
    yesterday_start = now - timedelta(days=1)

    # 1. Fetch yesterday's activities (messages, deals, tasks)
    act_res = await db.execute(
        select(Activity)
        .where(Activity.user_id == user.id, Activity.created_at >= yesterday_start)
        .order_by(Activity.created_at.desc())
    )
    activities = act_res.scalars().all()

    # 2. Fetch yesterday's updated/new deals
    deal_res = await db.execute(
        select(Deal)
        .where(Deal.user_id == user.id, Deal.updated_at >= yesterday_start)
        .order_by(Deal.updated_at.desc())
    )
    deals = deal_res.scalars().all()

    # 3. Fetch active deals for priorities / pending follow-ups
    active_deals_res = await db.execute(
        select(Deal)
        .where(
            Deal.user_id == user.id,
            Deal.stage.in_(["lead", "qualified", "proposal", "negotiation"])
        )
        .order_by(Deal.probability.desc())
    )
    active_deals = active_deals_res.scalars().all()

    # Format description for LLM
    act_summary = []
    for a in activities:
        act_summary.append(f"- Activity: Type={a.type}, Subject={a.subject or ''}, Content={(a.content or '')[:200]}")

    deal_summary = []
    for d in deals:
        deal_summary.append(f"- Deal: Title={d.title}, Stage={d.stage}, Amount={d.amount} {d.currency}, Probability={d.probability}%")

    priority_summary = []
    for d in active_deals:
        priority_summary.append(f"- Priority Deal (Stage={d.stage}): Title={d.title}, Amount={d.amount} {d.currency}, Probability={d.probability}%")

    prompt = f"""You are an executive CRM assistant.
Generate a concise, professional daily digest for the user {user.name}.

Yesterday's Activities:
{chr(10).join(act_summary) if act_summary else "No activities recorded yesterday."}

Yesterday's Updated/New Deals:
{chr(10).join(deal_summary) if deal_summary else "No deals updated yesterday."}

Today's Priorities (Active Deals / Follow-ups):
{chr(10).join(priority_summary) if priority_summary else "No active deals."}

Format the response beautifully as a telegram/email friendly message.
Highlight:
1. Summary of yesterday's activities.
2. Today's priorities (highlighting upcoming deadlines, low probability/stuck deals, or follow-ups).
Keep it clean, concise, and actionable."""

    try:
        digest_text = await call_llm(
            system="You are a helpful, professional CRM assistant. Keep messages concise and clear.",
            user=prompt,
            user_id=user.id
        )
    except Exception as e:
        log.error(f"Failed to generate digest text for user {user.id}: {e}")
        digest_text = (
            f"Daily Digest for {user.name}:\n\n"
            f"Yesterday: {len(activities)} activities, {len(deals)} deals updated.\n"
            f"Today: {len(active_deals)} active deals to prioritize.\n\n"
            f"Unable to generate detailed summary (LLM service error)."
        )

    # 4. After processing the data, send to Telegram bot Aladdin Aliyev
    # После обработки данных отправить мне в телеграм бот Aladdin Aliyev
    telegram_sent = False

    # Check global settings for Telegram bot token & chat ID
    if settings.telegram_bot_token and settings.telegram_chat_id:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                    json={"chat_id": settings.telegram_chat_id, "text": digest_text},
                )
                if resp.status_code == 200:
                    log.info(f"Daily digest sent via global Telegram settings to chat {settings.telegram_chat_id}")
                    telegram_sent = True
        except Exception as e:
            log.error(f"Failed to send daily digest via global Telegram settings: {e}")

    # Fallback/additional try to send via user's configured messaging channels
    if not telegram_sent:
        from app.models.messaging_channel import MessagingChannel
        from app.services.messaging_service import send_telegram as service_send_telegram

        channel_res = await db.execute(
            select(MessagingChannel).where(
                MessagingChannel.user_id == user.id,
                MessagingChannel.type == "telegram",
                MessagingChannel.status == "connected"
            )
        )
        channel = channel_res.scalars().first()
        if channel:
            # Send to Aladdin Aliyev via chat ID in channel configuration or contact list
            from app.models.contact import Contact
            contact_res = await db.execute(
                select(Contact).where(
                    Contact.user_id == user.id,
                    Contact.name.ilike("%Aladdin Aliyev%")
                )
            )
            contact = contact_res.scalars().first()
            chat_id = contact.phone if (contact and contact.phone) else (channel.config or {}).get("chat_id")
            if chat_id:
                try:
                    await service_send_telegram(channel, str(chat_id), digest_text)
                    log.info(f"Daily digest sent via Telegram channel {channel.id} to chat {chat_id}")
                    telegram_sent = True
                except Exception as e:
                    log.error(f"Failed to send daily digest via Telegram channel: {e}")

    # 5. Send via Email as a preferred channel fallback
    email_res = await db.execute(
        select(EmailAccount).where(
            EmailAccount.user_id == user.id,
            EmailAccount.status == "connected"
        )
    )
    email_account = email_res.scalars().first()
    if email_account:
        from app.services.email_service import send_email as service_send_email
        try:
            await service_send_email(
                db=db,
                account=email_account,
                to_email=user.email,
                subject=f"Daily CRM Digest - {now.strftime('%Y-%m-%d')}",
                body=digest_text
            )
            log.info(f"Daily digest sent via Email to {user.email}")
        except Exception as e:
            log.error(f"Failed to send daily digest email to {user.email}: {e}")


# [RCF:PROTECTED]
@scheduler.scheduled_job("cron", hour=9, minute=0)
# [RCF:PROTECTED]
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


# [RCF:PROTECTED]
@scheduler.scheduled_job("cron", hour=9, minute=30)
# [RCF:PROTECTED]
async def daily_digest_job():
    """Daily job to generate and send daily digest of CRM activities, deals, and tasks."""
    log.info("Starting daily digest job")
    try:
        async with async_session() as db:
            users_res = await db.execute(select(User))
            users = users_res.scalars().all()
            for user in users:
                await send_user_daily_digest(db, user)
        log.info("Daily digest job completed successfully")
    except Exception as e:
        log.error(f"Daily digest job failed: {e}", exc_info=True)


# [RCF:PROTECTED]
@scheduler.scheduled_job("cron", day_of_week="fri", hour=17, minute=0)
# [RCF:PROTECTED]
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


# [RCF:PROTECTED]
def start_scheduler():
    """Start the autonomous bot scheduler."""
    scheduler.start()
    log.info("Autonomous bot scheduler started")


# [RCF:PROTECTED]
def stop_scheduler():
    """Stop the autonomous bot scheduler."""
    scheduler.shutdown()
    log.info("Autonomous bot scheduler stopped")
