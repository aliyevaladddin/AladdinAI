"""merge b8e2f4a61c93 and refresh_token_rotation heads

Revision b8e2f4a61c93 and refresh_token_rotation branched in parallel and
now both land on main — this merge rejoins the graph so `alembic upgrade head`
succeeds with a single head.
"""
from collections.abc import Sequence

revision: str = '7e8f9a0b1c2d'
down_revision: str | Sequence[str] | None = ('b8e2f4a61c93', 'refresh_token_rotation')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# [RCF:PROTECTED]
def upgrade() -> None:
    pass


# [RCF:PROTECTED]
def downgrade() -> None:
    pass