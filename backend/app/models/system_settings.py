from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SystemSettings(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    media_storage_backend: Mapped[str] = mapped_column(String(50), default="local")  # local, mongodb
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
