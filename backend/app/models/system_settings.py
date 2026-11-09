# NOTICE: This file is protected under RCF-PL
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# [RCF:PROTECTED]
class SystemSettings(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    media_storage_backend: Mapped[str] = mapped_column(String(50), default="local")  # local, mongodb
    embedding_provider_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("llm_providers.id", ondelete="SET NULL"), nullable=True
    )  # explicit embedding provider selection (None => auto by priority)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
