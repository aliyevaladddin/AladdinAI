# NOTICE: This file is protected under RCF-PL
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# [RCF:PROTECTED]
class MCPServer(Base):
    """A user-scoped external Model Context Protocol server (Streamable HTTP).

    `headers_encrypted` stores the whole {header: value} JSON blob encrypted
    at rest — header values (auth tokens) never leave the backend in
    plaintext. `tools_cache` holds the last successful tools/list result so
    agent runners can build schemas without a round-trip.
    """

    __tablename__ = "mcp_servers"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_mcp_servers_user_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(500))
    headers_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    tools_cache: Mapped[list | None] = mapped_column(JSON, nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
