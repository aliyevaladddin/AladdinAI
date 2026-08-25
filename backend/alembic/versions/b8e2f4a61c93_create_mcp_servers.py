# NOTICE: This file is protected under RCF-PL
"""create mcp_servers table

Revision ID: b8e2f4a61c93
Revises: a7c3e91b4d52
Create Date: 2026-08-25 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8e2f4a61c93"
down_revision: Union[str, Sequence[str], None] = "a7c3e91b4d52"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# [RCF:PROTECTED]
def upgrade() -> None:
    # Guard: skip any table already present (dialect-agnostic; safe on both the
    # Postgres CI run and any environment where a table was created out of band).
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())

    if "mcp_servers" not in existing:
        op.create_table(
            "mcp_servers",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("url", sa.String(length=500), nullable=False),
            sa.Column("headers_encrypted", sa.Text(), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column(
                "timeout_seconds", sa.Integer(), nullable=False, server_default="30",
            ),
            sa.Column("tools_cache", sa.JSON(), nullable=True),
            sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "name", name="uq_mcp_servers_user_name"),
        )
        op.create_index(
            "ix_mcp_servers_user_id", "mcp_servers", ["user_id"],
        )


# [RCF:PROTECTED]
def downgrade() -> None:
    bind = op.get_bind()
    if "mcp_servers" in set(sa.inspect(bind).get_table_names()):
        op.drop_table("mcp_servers")
