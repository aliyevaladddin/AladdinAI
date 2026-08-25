# NOTICE: This file is protected under RCF-PL v2.0.3
# [RCF:PROTECTED]
"""
File version — one immutable snapshot of a file's content. Append-only by
contract: inserts only, no updates, no deletes. Restoring an old version
inserts a NEW row pointing at the same storage_ref — history is never
rewritten.

storage_ref is the JSON dict returned by media_storage.save_bytes stored
as Text (SQLite compatibility). It is backend-specific: {"file_id": ...}
for MongoDB/GridFS or {"path": ...} for local disk.

uploader_user_id matters beyond attribution: media_mongo scopes blobs to
the uploading user (get_bytes verifies metadata.user_id), so every read of
this version's bytes must pass THIS user id to the storage layer, while
authorization happens at the workspace API via space membership.

author_type/agent_run_id prepare phase 3: agent-written versions carry
author_type='agent' and the responsible run.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# [RCF:PROTECTED]
class FileVersion(Base):
    __tablename__ = "file_versions"
    __table_args__ = (
        UniqueConstraint("file_id", "version_no", name="uq_file_version_no"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    file_id: Mapped[int] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE"), index=True,
    )
    version_no: Mapped[int] = mapped_column(Integer)

    storage_ref: Mapped[str] = mapped_column(Text)
    byte_size: Mapped[int] = mapped_column(Integer, default=0)

    # Blob scope owner — see module docstring before touching this.
    uploader_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )

    author_type: Mapped[str] = mapped_column(String(20), default="human")
    agent_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc),
    )
