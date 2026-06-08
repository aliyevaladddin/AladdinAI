from html.parser import HTMLParser
import logging
import os
import re
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.activity import Activity
from app.models.agent import Agent
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.messaging_channel import MessagingChannel
from app.models.user import User
from app.schemas.crm import ActivityCreate, ActivityResponse
from app.security import get_current_user
from app.services.agent_runner import run_agent
from app.services.llm_service import LLMError

log = logging.getLogger(__name__)

router = APIRouter(prefix="/crm/activities", tags=["crm"])

ATTACHMENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "media", "attachments")
ATTACHMENTS_ROOT = os.path.realpath(ATTACHMENTS_DIR)


@router.get("", response_model=list[ActivityResponse])
async def list_activities(
    type: str | None = None,
    channel: str | None = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Activity).where(Activity.user_id == user.id)
    if type:
        types = type.split(",")
        q = q.where(Activity.type.in_(types))
    if channel:
        q = q.where(Activity.channel == channel)
    result = await db.execute(q.order_by(Activity.created_at.desc()).limit(limit))
    return result.scalars().all()


@router.post("", response_model=ActivityResponse, status_code=201)
async def create_activity(body: ActivityCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    activity = Activity(user_id=user.id, **body.model_dump())
    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    return activity

class ActivityUpdate(BaseModel):
    contact_id: int | None = None

@router.patch("/{activity_id}", response_model=ActivityResponse)
async def update_activity(
    activity_id: int,
    body: ActivityUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Activity).where(Activity.id == activity_id, Activity.user_id == user.id)
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    if body.contact_id is not None:
        activity.contact_id = body.contact_id
        
    await db.commit()
    await db.refresh(activity)
    return activity

@router.get("/{activity_id}/attachments/{filename}")
async def download_attachment(
    activity_id: int,
    filename: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download or preview an email attachment by activity ID and filename."""
    # Sanitize and validate filename to prevent path traversal
    safe_filename = os.path.basename(filename)
    if safe_filename != filename or not safe_filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    result = await db.execute(
        select(Activity).where(Activity.id == activity_id, Activity.user_id == user.id)
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Validate filename exists in activity metadata
    attachments = (activity.metadata_json or {}).get("attachments", [])
    meta = next((a for a in attachments if a["filename"] == safe_filename), None)
    if not meta:
        raise HTTPException(status_code=404, detail="Attachment not found")

    activity_dir = os.path.realpath(os.path.join(ATTACHMENTS_ROOT, str(activity_id)))
    if not activity_dir.startswith(ATTACHMENTS_ROOT + os.sep):
        raise HTTPException(status_code=404, detail="Attachment not found")

    file_path = os.path.realpath(os.path.join(activity_dir, safe_filename))
    if not file_path.startswith(activity_dir + os.sep) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Attachment not found")

    return FileResponse(
        path=file_path,
        filename=safe_filename,
        media_type=meta.get("content_type", "application/octet-stream"),
    )


# ── Suggested replies ────────────────────────────────────────────────

class SuggestReplyResponse(BaseModel):
    draft: str
    agent_id: int
    agent_name: str


class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.text = []
        self.ignore = False
        self.ignore_tags = {"script", "style"}

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.ignore_tags:
            self.ignore = True
        elif tag.lower() in {"br"}:
            self.text.append("\n")
        elif tag.lower() in {"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.text.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() in self.ignore_tags:
            self.ignore = False
        elif tag.lower() in {"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.text.append("\n")

    def handle_data(self, d):
        if not self.ignore:
            self.text.append(d)

    def get_data(self):
        return "".join(self.text)


def _strip_html(s: str | None) -> str:
    if not s:
        return ""
    if "<" not in s:
        return s.strip()
    try:
        parser = MLStripper()
        parser.feed(s)
        text = parser.get_data()
    except Exception:
        # Fallback to simple regex if HTMLParser fails
        text = re.sub(r"<[^>]+>", " ", s)

    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    return text.strip()


def _normalize_subject(s: str | None) -> str:
    if not s:
        return ""
    return re.sub(r"^(\s*(re|fwd|fw|aw)\s*:\s*)+", "", s, flags=re.IGNORECASE).strip()


async def _pick_agent(
    db: AsyncSession, user: User, activity: Activity
) -> Agent | None:
    """Resolve the agent that should draft a reply for this activity.

    Priority: deal.assigned_agent → messaging channel's agent → first agent.
    """
    # 1. Deal assignment via contact's most recent deal
    if activity.contact_id:
        deal = (
            await db.execute(
                select(Deal)
                .where(
                    Deal.contact_id == activity.contact_id,
                    Deal.user_id == user.id,
                    Deal.assigned_agent_id.is_not(None),
                )
                .order_by(Deal.updated_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if deal and deal.assigned_agent_id:
            agent = (
                await db.execute(
                    select(Agent).where(
                        Agent.id == deal.assigned_agent_id, Agent.user_id == user.id
                    )
                )
            ).scalar_one_or_none()
            if agent:
                return agent

    # 2. Messaging channel assignment (telegram/whatsapp/sms)
    if activity.channel and activity.channel not in ("gmail", "outlook", "imap", "email"):
        ch = (
            await db.execute(
                select(MessagingChannel).where(
                    MessagingChannel.user_id == user.id,
                    MessagingChannel.type == activity.channel,
                    MessagingChannel.agent_id.is_not(None),
                )
            )
        ).scalar_one_or_none()
        if ch and ch.agent_id:
            agent = (
                await db.execute(
                    select(Agent).where(Agent.id == ch.agent_id, Agent.user_id == user.id)
                )
            ).scalar_one_or_none()
            if agent:
                return agent

    # 3. Fallback: first agent the user has
    return (
        await db.execute(
            select(Agent).where(Agent.user_id == user.id).order_by(Agent.id).limit(1)
        )
    ).scalar_one_or_none()


async def _build_thread_context(
    db: AsyncSession, user: User, activity: Activity, max_prior: int = 4
) -> str:
    """Fetch prior messages in the same thread (by normalized subject + contact).

    Returns a formatted block 'From X (date): ...' lines, oldest first.
    """
    norm = _normalize_subject(activity.subject)
    if not norm:
        return ""
    q = (
        select(Activity)
        .where(
            Activity.user_id == user.id,
            Activity.id != activity.id,
            Activity.type.in_(["email_in", "email_out", "message_in", "message_out"]),
        )
        .order_by(Activity.created_at.desc())
        .limit(20)
    )
    if activity.contact_id:
        q = q.where(Activity.contact_id == activity.contact_id)
    rows = (await db.execute(q)).scalars().all()
    related = [
        a for a in rows
        if _normalize_subject(a.subject).lower() == norm.lower()
    ][:max_prior]
    related.reverse()  # oldest first

    parts = []
    for a in related:
        who = "You" if a.type.endswith("_out") else "Them"
        body = _strip_html(a.content)[:600]
        parts.append(f"--- {who} ({a.created_at:%b %d %H:%M}) ---\n{body}")
    return "\n\n".join(parts)


@router.post("/{activity_id}/suggest-reply", response_model=SuggestReplyResponse)
async def suggest_reply(
    activity_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a suggested reply draft for the given activity.

    Picks an agent via _pick_agent, builds a context-rich prompt from the
    activity + thread history + contact profile, and runs the agent. The
    draft is plain text, never auto-sent.
    """
    activity = (
        await db.execute(
            select(Activity).where(Activity.id == activity_id, Activity.user_id == user.id)
        )
    ).scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    if not activity.type.endswith("_in"):
        raise HTTPException(
            status_code=400, detail="Can only suggest replies for inbound messages"
        )

    agent = await _pick_agent(db, user, activity)
    if not agent:
        raise HTTPException(status_code=400, detail="No agent available to draft a reply")

    # Contact profile
    contact = None
    if activity.contact_id:
        contact = (
            await db.execute(
                select(Contact).where(
                    Contact.id == activity.contact_id, Contact.user_id == user.id
                )
            )
        ).scalar_one_or_none()

    profile_lines = []
    if contact:
        profile_lines.append(f"Name: {contact.name}")
        if contact.email:
            profile_lines.append(f"Email: {contact.email}")
        if contact.company:
            profile_lines.append(f"Company: {contact.company}")
        if contact.notes:
            profile_lines.append(f"Notes: {contact.notes}")
    profile = "\n".join(profile_lines) or "(unknown contact)"

    thread = await _build_thread_context(db, user, activity)
    body = _strip_html(activity.content)[:3000]
    channel = activity.channel or activity.type

    user_prompt = (
        f"Draft a reply to the message below. Match the tone of the conversation "
        f"so far. Keep it concise, friendly, and actionable. Do not include a "
        f"subject line or greeting like 'Dear ...' unless the prior messages used "
        f"them. Return ONLY the reply body — no markdown, no preamble.\n\n"
        f"=== Contact ===\n{profile}\n\n"
        f"=== Channel ===\n{channel}\n\n"
        + (f"=== Thread (oldest first) ===\n{thread}\n\n" if thread else "")
        + f"=== Latest message to reply to ===\n"
        f"Subject: {activity.subject or '(no subject)'}\n\n{body}"
    )

    # Use agent's existing system prompt but suppress tool use for this turn —
    # we only want a textual draft. agent_runner will short-circuit when the
    # model returns a final message with no tool calls.
    messages = [
        {"role": "system", "content": agent.system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        draft = await run_agent(db, agent, messages, extras={"mode": "suggest_reply"})
    except LLMError as e:
        log.warning("suggest_reply failed for activity %s: %s", activity_id, e)
        raise HTTPException(status_code=502, detail=f"Agent error: {e}")

    return SuggestReplyResponse(
        draft=(draft or "").strip(),
        agent_id=agent.id,
        agent_name=agent.name,
    )
