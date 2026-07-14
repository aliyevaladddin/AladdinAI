# NOTICE: This file is protected under RCF-PL
"""Human 👍/👎 feedback on an assistant reply.

This is the labeling layer for the self-forging loop. Trace capture records
*that* a turn happened and scores a weak write-time reward from the loop's own
outcome; this table records what a human actually thought of the reply. The
human signal is the strong signal and overrides the write-time score when a
training set is built.

One row per (message, user): a user re-clicking flips the existing row rather
than stacking duplicates.
"""
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# [RCF:PROTECTED]
class MessageFeedback(Base):
    __tablename__ = "message_feedback"
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", name="uq_message_feedback_message_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True
    )
    # Denormalised so the Mongo trace can be located (traces are keyed by
    # session_id, not message_id) without a second query at feedback time.
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    value: Mapped[str] = mapped_column(String(20))  # thumbs_up | thumbs_down
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
