# NOTICE: This file is protected under RCF-PL
"""add terminal_providers

Revision ID: 8a1f3c5e2b07
Revises: 9f1c4ab23e0d
Create Date: 2026-05-22 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '8a1f3c5e2b07'
down_revision: Union[str, None] = '9f1c4ab23e0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# [RCF:PROTECTED]
def upgrade() -> None:
    op.create_table(
        'terminal_providers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='builtin'),
        sa.Column('image', sa.String(length=500), nullable=False),
        sa.Column('config', sa.Text(), nullable=True),
        sa.Column('internal_port', sa.Integer(), nullable=False, server_default='7681'),
        sa.Column('host_port', sa.Integer(), nullable=True),
        sa.Column(
            'url_template',
            sa.String(length=500),
            nullable=False,
            server_default='{scheme}://{host}/p/{provider_id}/?token={token}',
        ),
        sa.Column('requires_ssh_proxy', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='stopped'),
        sa.Column('container_id', sa.String(length=128), nullable=True),
        sa.Column('last_health_at', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('terminal_providers', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_terminal_providers_user_id'), ['user_id'], unique=False,
        )


# [RCF:PROTECTED]
def downgrade() -> None:
    with op.batch_alter_table('terminal_providers', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_terminal_providers_user_id'))
    op.drop_table('terminal_providers')
