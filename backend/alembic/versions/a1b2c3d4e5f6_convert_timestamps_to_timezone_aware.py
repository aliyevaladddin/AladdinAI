"""convert all TIMESTAMP columns to TIMESTAMP WITH TIME ZONE

Revision ID: a1b2c3d4e5f6
Revises: 4d80430a55ae
Create Date: 2026-05-31 06:48:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '20260530050616'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# All (table, column) pairs that use TIMESTAMP WITHOUT TIME ZONE
TIMESTAMP_COLUMNS = [
    ("users", "created_at"),
    ("contacts", "created_at"),
    ("deals", "created_at"),
    ("activities", "created_at"),
    ("agents", "created_at"),
    ("agent_messages", "created_at"),
    ("agent_triggers", "created_at"),
    ("agent_triggers", "last_fired_at"),
    ("agent_triggers", "next_fire_at"),
    ("chat_sessions", "created_at"),
    ("chat_messages", "created_at"),
    ("conversations", "created_at"),
    ("email_accounts", "created_at"),
    ("llm_providers", "created_at"),
    ("messaging_channels", "created_at"),
    ("mongo_connections", "created_at"),
    ("bentoml_connections", "created_at"),
    ("notifications", "created_at"),
    ("outgoing_webhooks", "created_at"),
    ("router_configs", "created_at"),
    ("terminal_providers", "created_at"),
    ("vms", "created_at"),
]


def upgrade() -> None:
    for table, column in TIMESTAMP_COLUMNS:
        op.execute(
            f"ALTER TABLE {table} "
            f"ALTER COLUMN {column} "
            f"TYPE TIMESTAMP WITH TIME ZONE "
            f"USING {column} AT TIME ZONE 'UTC'"
        )


def downgrade() -> None:
    for table, column in TIMESTAMP_COLUMNS:
        op.execute(
            f"ALTER TABLE {table} "
            f"ALTER COLUMN {column} "
            f"TYPE TIMESTAMP WITHOUT TIME ZONE "
            f"USING {column} AT TIME ZONE 'UTC'"
        )
