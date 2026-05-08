from datetime import datetime, timezone

from sqlalchemy import Boolean, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AgentTrigger(Base):
    """Cron-style trigger that fans out to one or more agents.

    On fire we INSERT one row per agent_id into agent_messages — the existing
    background worker handles execution. Schedule fields:

    - schedule_kind: how the user authored it (`preset` | `cron`). UI uses this
      to decide which editor to open. The actual cron expression is always
      stored in `cron`, regardless of kind.
    - cron: 5-field cron expression in UTC.
    """
    __tablename__ = "agent_triggers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))

    schedule_kind: Mapped[str] = mapped_column(String(20), default="cron")
    schedule_preset: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cron: Mapped[str] = mapped_column(String(100))

    agent_ids: Mapped[list] = mapped_column(JSON, default=list)
    task_template: Mapped[str] = mapped_column(Text)
    context_template: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_fired_at: Mapped[datetime | None] = mapped_column(nullable=True)
    next_fire_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
