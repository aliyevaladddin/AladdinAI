"""add attachments column to chat_messages

Revision ID: 9f1c4ab23e0d
Revises: 7e4a9b2c0f15
Create Date: 2026-05-14
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "9f1c4ab23e0d"
down_revision: Union[str, None] = "7e4a9b2c0f15"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    with op.batch_alter_table("chat_messages") as batch:
        batch.add_column(sa.Column("attachments", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("chat_messages") as batch:
        batch.drop_column("attachments")
