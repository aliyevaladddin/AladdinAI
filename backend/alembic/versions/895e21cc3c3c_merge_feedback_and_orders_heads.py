# NOTICE: This file is protected under RCF-PL
"""merge feedback and orders heads

Two migrations branched off c1d2e3f4a5b6 in parallel and both landed on main:
  * d3f7a9c1e2b8 — message_feedback table (self-forging 👍/👎 layer)
  * e5a1b7c93f24 — products / orders / order_items
That left the revision graph with two heads, so `alembic upgrade head` failed
with "multiple heads". This is a no-op merge that rejoins the graph into a
single head — no schema change of its own.

Revision ID: 895e21cc3c3c
Revises: d3f7a9c1e2b8, e5a1b7c93f24
Create Date: 2026-07-14 17:11:24.370010
"""
from typing import Sequence, Union


revision: str = '895e21cc3c3c'
down_revision: Union[str, Sequence[str], None] = ('d3f7a9c1e2b8', 'e5a1b7c93f24')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# [RCF:PROTECTED]
def upgrade() -> None:
    pass


# [RCF:PROTECTED]
def downgrade() -> None:
    pass
