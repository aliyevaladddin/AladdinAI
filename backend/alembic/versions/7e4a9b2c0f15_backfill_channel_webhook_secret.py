"""backfill webhook_secret for existing messaging channels

Revision ID: 7e4a9b2c0f15
Revises: 66adfe6c7cf3
Create Date: 2026-05-10

New channels get a random webhook_secret on creation. Channels that existed
before that change have NULL, which breaks signature verification. Generate
one for each so they continue to work — users still need to push the new
value to Telegram (setWebhook) / Meta (verify_token) / WAHA (HMAC config)
to complete the loop. Output is logged at migration time so the operator
can copy it.
"""
from __future__ import annotations

import secrets
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "7e4a9b2c0f15"
down_revision: Union[str, None] = "66adfe6c7cf3"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, name, type FROM messaging_channels WHERE webhook_secret IS NULL")
    ).fetchall()

    for row in rows:
        generated_val = secrets.token_urlsafe(32)
        bind.execute(
            sa.text("UPDATE messaging_channels SET webhook_secret = :s WHERE id = :id"),
            {"s": generated_val, "id": row.id},
        )
        print(
            f"[migration 7e4a9b2c0f15] channel id={row.id} ({row.type}: {row.name!r}) "
            f"new config value={generated_val} — update the provider side to match."
        )


def downgrade() -> None:
    # Backfill is idempotent — leaving the secrets in place on downgrade is
    # harmless and avoids breaking channels if you re-upgrade later.
    pass
