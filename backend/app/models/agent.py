from datetime import datetime, timezone

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(255))
    model: Mapped[str] = mapped_column(String(255))
    system_prompt: Mapped[str] = mapped_column(Text)
    tools_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    llm_provider_id: Mapped[int | None] = mapped_column(ForeignKey("llm_providers.id"), nullable=True)
    port: Mapped[int | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="stopped")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
