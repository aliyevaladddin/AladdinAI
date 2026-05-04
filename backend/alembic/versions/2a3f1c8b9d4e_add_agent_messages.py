"""add agent_messages table

Revision ID: 2a3f1c8b9d4e
Revises: 1f892d4f16e3
Create Date: 2026-05-04 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2a3f1c8b9d4e'
down_revision: Union[str, None] = '1f892d4f16e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'agent_messages',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('from_agent_id', sa.Integer(), sa.ForeignKey('agents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('to_agent_id', sa.Integer(), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parent_session_id', sa.Integer(), sa.ForeignKey('chat_sessions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('task', sa.Text(), nullable=False),
        sa.Column('context', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_agent_messages_to_agent_status', 'agent_messages', ['to_agent_id', 'status'])
    op.create_index('ix_agent_messages_parent_session', 'agent_messages', ['parent_session_id'])


def downgrade() -> None:
    op.drop_index('ix_agent_messages_parent_session', table_name='agent_messages')
    op.drop_index('ix_agent_messages_to_agent_status', table_name='agent_messages')
    op.drop_table('agent_messages')
