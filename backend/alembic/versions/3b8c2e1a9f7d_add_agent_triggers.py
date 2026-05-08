"""add agent_triggers table

Revision ID: 3b8c2e1a9f7d
Revises: 2a3f1c8b9d4e
Create Date: 2026-05-08 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3b8c2e1a9f7d'
down_revision: Union[str, None] = '2a3f1c8b9d4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'agent_triggers',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('schedule_kind', sa.String(length=20), nullable=False, server_default='cron'),
        sa.Column('schedule_preset', sa.String(length=50), nullable=True),
        sa.Column('cron', sa.String(length=100), nullable=False),
        sa.Column('agent_ids', sa.JSON(), nullable=False),
        sa.Column('task_template', sa.Text(), nullable=False),
        sa.Column('context_template', sa.JSON(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('last_fired_at', sa.DateTime(), nullable=True),
        sa.Column('next_fire_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_agent_triggers_user_enabled', 'agent_triggers', ['user_id', 'enabled'])


def downgrade() -> None:
    op.drop_index('ix_agent_triggers_user_enabled', table_name='agent_triggers')
    op.drop_table('agent_triggers')
