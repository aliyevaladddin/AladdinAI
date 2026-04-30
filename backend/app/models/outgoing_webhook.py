from datetime import datetime, timezone
from sqlalchemy import ForeignKey, String, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class OutgoingWebhook(Base):
    __tablename__ = "outgoing_webhooks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(500))
    secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    events: Mapped[list[str]] = mapped_column(JSON) # e.g. ["message_received", "deal_created"]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_marker: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
