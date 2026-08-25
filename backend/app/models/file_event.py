# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""
File event — the audit ledger ("timeline") of everything that happened to
a file. Append-only by contract: inserts only, no updates, no deletes.

Event types written today: created, version_added, downloaded, restored,
moved, deleted, member_changed. Phase 3 adds agent events (proposed_change,
approved) with actor_type='agent' — that is why actor identity is split
into actor_type + actor_user_id instead of a single FK.

payload carries small JSON details (old/new folder id, version number) as
Text for SQLite compatibility.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# [RCF:PROTECTED]
class FileEvent(Base):
    __tablename__ = "file_events"
    __table_args__ = (
        Index("ix_file_events_file_created", "file_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    file_id: Mapped[int] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE"), index=True,
    )
    event_type: Mapped[str] = mapped_column(String(40))
    actor_type: Mapped[str] = mapped_column(String(20), default="human")
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc),
    )
