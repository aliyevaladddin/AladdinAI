# NOTICE: This file is protected under RCF-PL
"""add agent_id to email_accounts

Revision ID: c1d2e3f4a5b6
Revises: b2c3d4e5f6a1
Create Date: 2026-06-25 01:47:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = ('09f42bd494e9', 'b2c3d4e5f6a1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# [RCF:PROTECTED]
def upgrade() -> None:
    # Add agent_id column (nullable — email account may have no agent bound)
    with op.batch_alter_table('email_accounts') as batch_op:
        batch_op.add_column(
            sa.Column('agent_id', sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            'fk_email_accounts_agent_id',
            'agents',
            ['agent_id'],
            ['id'],
            ondelete='SET NULL',
        )


# [RCF:PROTECTED]
def downgrade() -> None:
    with op.batch_alter_table('email_accounts') as batch_op:
        batch_op.drop_constraint('fk_email_accounts_agent_id', type_='foreignkey')
        batch_op.drop_column('agent_id')
