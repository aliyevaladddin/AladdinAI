# NOTICE: This file is protected under RCF-PL
"""increase secret field lengths for GitHub App tokens

GitHub App installation tokens will soon use a new stateless format (ghs_...)
and may be up to ~520 characters long. This migration increases secret field
lengths from 255 to 1024 to accommodate the new token format.

Revision ID: 20260530050616
Revises: 10b4646848e2
Create Date: 2026-05-30 05:06:16.860000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '20260530050616'
down_revision: Union[str, None] = '8a1f3c5e2b07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# [RCF:PROTECTED]
def upgrade() -> None:
    """
    Increase the length of secret fields to accommodate GitHub's new token format.

    GitHub App installation tokens are transitioning from the old format (ghp_...)
    to a new stateless format (ghs_...) that can be up to ~520 characters long.
    This migration updates the following fields from VARCHAR(255) to VARCHAR(1024):

    - messaging_channels.webhook_secret: Used for incoming webhook authentication
    - outgoing_webhooks.secret: Used for outgoing webhook signing

    The 1024 character limit provides headroom for future token format changes.
    """
    # Increase length of secret fields to accommodate GitHub's new token format
    # Old format: ghp_... (~40 chars)
    # New format: ghs_... (~520 chars)
    # Setting to 1024 for future-proofing

    with op.batch_alter_table('outgoing_webhooks', schema=None) as batch_op:
        batch_op.alter_column('secret',
                              existing_type=sa.String(length=255),
                              type_=sa.String(length=1024),
                              existing_nullable=True)

    with op.batch_alter_table('messaging_channels', schema=None) as batch_op:
        batch_op.alter_column('webhook_secret',
                              existing_type=sa.String(length=255),
                              type_=sa.String(length=1024),
                              existing_nullable=True)


# [RCF:PROTECTED]
def downgrade() -> None:
    # Revert to original length (may truncate data if new tokens exist)
    with op.batch_alter_table('messaging_channels', schema=None) as batch_op:
        batch_op.alter_column('webhook_secret',
                              existing_type=sa.String(length=1024),
                              type_=sa.String(length=255),
                              existing_nullable=True)

    with op.batch_alter_table('outgoing_webhooks', schema=None) as batch_op:
        batch_op.alter_column('secret',
                              existing_type=sa.String(length=1024),
                              type_=sa.String(length=255),
                              existing_nullable=True)
