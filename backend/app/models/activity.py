from datetime import datetime, timezone

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id", ondelete="CASCADE"))
    deal_id: Mapped[int | None] = mapped_column(ForeignKey("deals.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(50))  # email_in, email_out, message_in, message_out, note, call
    channel: Mapped[str | None] = mapped_column(String(50), nullable=True)  # gmail, telegram, whatsapp, sms
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
