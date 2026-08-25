# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""
Workspace file — the metadata row for one document in a space.

This row never holds bytes: content lives in the media storage backend and
is referenced by file_versions.storage_ref. The row is soft-deleted
(deleted_at) so timelines and audit history survive a "delete".

current_version_no is a denormalized pointer to the latest file_versions
entry; it is bumped inside the same transaction that inserts the version.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# [RCF:PROTECTED]
class WorkspaceFile(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(primary_key=True)
    space_id: Mapped[int] = mapped_column(
        ForeignKey("spaces.id", ondelete="CASCADE"), index=True,
    )
    folder_id: Mapped[int | None] = mapped_column(
        ForeignKey("folders.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    name: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    byte_size: Mapped[int] = mapped_column(Integer, default=0)

    # Denormalized latest version number; 0 until the first version lands.
    current_version_no: Mapped[int] = mapped_column(Integer, default=0)

    # Logical link to the file_versions.id this entry was derived from
    # (round-trip import in later phases). Plain integer on purpose: an FK
    # here would create a files <-> file_versions cycle that SQLite's
    # create_all cannot order.
    source_version_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )

    # Soft delete — audit history must survive a delete.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc),
    )
