from datetime import datetime, timezone

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MessagingChannel(Base):
    __tablename__ = "messaging_channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(50))  # telegram, whatsapp, sms
    name: Mapped[str] = mapped_column(String(255))
    config: Mapped[dict] = mapped_column(JSON)  # bot_token for telegram, phone_number_id for whatsapp, etc.
    webhook_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="disconnected")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
