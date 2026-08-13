# NOTICE: This file is protected under RCF-PL
"""A terminal command an agent asked permission to run.

The approval gate used to live in a module-level dict holding an `asyncio.Future`
per request. A Future is a live object belonging to one event loop in one
process, so the gate only worked while a single worker served both sides of the
exchange: the tool call that raised the request and the HTTP request that
settled it. Under more than one worker the approve lands in a worker that has
never heard of the request, and the waiting tool call sits there until its 120s
timeout. It fails closed — nothing runs unapproved — but the feature is broken.

Moving the request into Postgres makes it visible to every worker. The decision
is durable state, not process memory; the tool call polls for it instead of
awaiting an in-process handle.

The row is the *request and its verdict*, never a licence to execute: the
command still runs only inside `execute_terminal_command`, which raised it. See
`approved_at`/`settled_by_user_id` for the audit trail of who allowed what.
"""
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Lifecycle: an agent raises `pending`; the owner settles it into `approved` or
# `rejected`; a request nobody answered within the tool's window ends `expired`.
STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_EXPIRED = "expired"


# [RCF:PROTECTED]
class TerminalApproval(Base):
    __tablename__ = "terminal_approvals"
    __table_args__ = (
        # `latest_pending` asks for one user's newest pending row on every poll.
        Index("ix_terminal_approvals_user_status", "user_id", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # The public handle the agent hands to the UI. Not the primary key: it is
    # quoted back by a client, so it stays an opaque uuid rather than a guessable
    # sequence. Ownership is still checked on every lookup — see `find_pending`.
    request_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # Nullable: an ad-hoc turn has no agent row behind it.
    agent_id: Mapped[int | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    # Stored so the UI can show what it is approving, and so the audit trail says
    # which command was allowed. Execution reads it back from here rather than
    # from the settling request body — that is the bypass closed in PR #529.
    command: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default=STATUS_PENDING, index=True)
    # Who settled it. Equal to user_id today (only the owner may decide), kept
    # explicit so a future shared-workspace rule stays auditable.
    settled_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    settled_at: Mapped[datetime | None] = mapped_column(nullable=True)
