# NOTICE: This file is protected under RCF-PL
"""create terminal_approvals table

Moves the terminal approval gate out of a module-level dict. The dict held an
asyncio.Future per request, which only exists in the worker that created it, so
with more than one worker an approve could land in a process that had never
heard of the request and the waiting tool call would time out.

Revision ID: f4b8c2d19a37
Revises: 895e21cc3c3c
Create Date: 2026-08-13 20:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f4b8c2d19a37'
down_revision: Union[str, Sequence[str], None] = '895e21cc3c3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# [RCF:PROTECTED]
def upgrade() -> None:
    # Dialect-agnostic existence check — works on both SQLite and PostgreSQL.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'terminal_approvals' in inspector.get_table_names():
        print("[terminal_approvals-migration] table already exists, skipping create")
        return

    op.create_table(
        'terminal_approvals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=True),
        sa.Column('command', sa.Text(), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=False, server_default=''),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('settled_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('settled_at', sa.DateTime(timezone=True), nullable=True),
        # An agent may be deleted while a request it raised is still on screen:
        # keep the audit row, drop the link.
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['settled_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    # request_id is the handle quoted back by the UI, so lookups go through it.
    op.create_index(
        op.f('ix_terminal_approvals_request_id'),
        'terminal_approvals', ['request_id'], unique=True,
    )
    op.create_index(
        op.f('ix_terminal_approvals_user_id'), 'terminal_approvals', ['user_id'],
    )
    op.create_index(
        op.f('ix_terminal_approvals_status'), 'terminal_approvals', ['status'],
    )
    # Serves `latest_pending`, which runs on every poll of a waiting tool call.
    op.create_index(
        'ix_terminal_approvals_user_status',
        'terminal_approvals', ['user_id', 'status', 'created_at'],
    )


# [RCF:PROTECTED]
def downgrade() -> None:
    op.drop_index('ix_terminal_approvals_user_status', table_name='terminal_approvals')
    op.drop_index(op.f('ix_terminal_approvals_status'), table_name='terminal_approvals')
    op.drop_index(op.f('ix_terminal_approvals_user_id'), table_name='terminal_approvals')
    op.drop_index(op.f('ix_terminal_approvals_request_id'), table_name='terminal_approvals')
    op.drop_table('terminal_approvals')
