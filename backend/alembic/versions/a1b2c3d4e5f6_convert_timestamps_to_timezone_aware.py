"""convert all TIMESTAMP columns to TIMESTAMP WITH TIME ZONE

Revision ID: a1b2c3d4e5f6
Revises: 20260530050616
Create Date: 2026-05-31 06:48:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '20260530050616'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Only tables that are guaranteed to exist (have a create_table migration).
# Sorted by creation order to avoid FK issues.
TIMESTAMP_COLUMNS = [
    ("users", "created_at"),
    ("bentoml_connections", "created_at"),
    ("contacts", "created_at"),
    ("email_accounts", "created_at"),
    ("llm_providers", "created_at"),
    ("mongo_connections", "created_at"),
    ("outgoing_webhooks", "created_at"),
    ("router_configs", "created_at"),
    ("vm_connections", "created_at"),
    ("agents", "created_at"),
    ("chat_sessions", "created_at"),
    ("conversations", "created_at"),
    ("deals", "created_at"),
    ("messaging_channels", "created_at"),
    ("activities", "created_at"),
    ("chat_messages", "created_at"),
    ("agent_messages", "created_at"),
    ("agent_triggers", "created_at"),
    ("agent_triggers", "last_fired_at"),
    ("agent_triggers", "next_fire_at"),
    ("terminal_providers", "created_at"),
]


def _table_exists(conn, table_name: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.tables "
            "  WHERE table_schema = 'public' AND table_name = :tname"
            ")"
        ),
        {"tname": table_name},
    )
    return result.scalar()


def upgrade() -> None:
    conn = op.get_bind()
    for table, column in TIMESTAMP_COLUMNS:
        if not _table_exists(conn, table):
            print(f"[timestamp-migration] skipping {table}.{column} — table does not exist")
            continue
        conn.execute(sa.text(
            f"ALTER TABLE {table} "
            f"ALTER COLUMN {column} "
            f"TYPE TIMESTAMP WITH TIME ZONE "
            f"USING {column} AT TIME ZONE 'UTC'"
        ))


def downgrade() -> None:
    conn = op.get_bind()
    for table, column in TIMESTAMP_COLUMNS:
        if not _table_exists(conn, table):
            continue
        conn.execute(sa.text(
            f"ALTER TABLE {table} "
            f"ALTER COLUMN {column} "
            f"TYPE TIMESTAMP WITHOUT TIME ZONE "
            f"USING {column} AT TIME ZONE 'UTC'"
        ))
