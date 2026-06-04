"""add system_settings table

Revision ID: 09f42bd494e9
Revises: aa0572bc48a8
Create Date: 2026-06-04 16:11:26.500433
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '09f42bd494e9'
down_revision: Union[str, None] = 'aa0572bc48a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'system_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('media_storage_backend', sa.String(length=50), nullable=False, server_default='local'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_system_settings_user_id'),
    )


def downgrade() -> None:
    op.drop_table('system_settings')
