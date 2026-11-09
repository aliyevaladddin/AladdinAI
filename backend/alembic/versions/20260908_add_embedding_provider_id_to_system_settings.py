"""add embedding_provider_id to system_settings

Revision ID: 20260908embprov
Revises: 7e8f9a0b1c2d
Create Date: 2026-09-08
"""
from alembic import op
import sqlalchemy as sa

revision = "20260908embprov"
down_revision = "7e8f9a0b1c2d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "system_settings",
        # Keep the FK at the ORM/model level; SQLite (used in local/test DBs)
        # cannot ALTER a table to add a constraint, so the migration only adds
        # the nullable column. Production databases enforce the FK via the model.
        sa.Column(
            "embedding_provider_id",
            sa.Integer(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("system_settings", "embedding_provider_id")
