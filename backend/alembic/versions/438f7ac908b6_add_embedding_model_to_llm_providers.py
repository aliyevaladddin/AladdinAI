"""add embedding_model to llm_providers

Revision ID: 438f7ac908b6
Revises: b2c3d4e5f6a1
Create Date: 2026-06-04 15:49:48.442956
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '438f7ac908b6'
down_revision: Union[str, None] = 'b2c3d4e5f6a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('llm_providers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('embedding_model', sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('llm_providers', schema=None) as batch_op:
        batch_op.drop_column('embedding_model')
