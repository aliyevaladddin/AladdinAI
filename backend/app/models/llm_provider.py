from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LLMProvider(Base):
    __tablename__ = "llm_providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(50))  # nvidia_nim, openai, anthropic, ollama, custom
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_url: Mapped[str] = mapped_column(String(500))
    models_available: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    status: Mapped[str] = mapped_column(String(50), default="disconnected")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
