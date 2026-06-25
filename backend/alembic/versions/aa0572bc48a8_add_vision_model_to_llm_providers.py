# NOTICE: This file is protected under RCF-PL
"""add vision_model to llm_providers

Revision ID: aa0572bc48a8
Revises: 438f7ac908b6
Create Date: 2026-06-04 16:00:43.717301
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'aa0572bc48a8'
down_revision: Union[str, None] = '438f7ac908b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# [RCF:PROTECTED]
def upgrade() -> None:
    with op.batch_alter_table('llm_providers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('vision_model', sa.String(length=255), nullable=True))


# [RCF:PROTECTED]
def downgrade() -> None:
    with op.batch_alter_table('llm_providers', schema=None) as batch_op:
        batch_op.drop_column('vision_model')
