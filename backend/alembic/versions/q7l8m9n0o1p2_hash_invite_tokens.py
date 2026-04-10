"""clear plaintext invite tokens (migrate to hashed storage)

Revision ID: q7l8m9n0o1p2
Revises: p6k7l8m9n0o1
Create Date: 2026-04-10 00:00:00.000000

Existing tokens were stored in plaintext. Now we store SHA-256 hashes.
Pending tokens cannot be migrated (we don't have the originals) so we
expire them — they were only test invites at this stage.
"""
from datetime import datetime, timezone
from alembic import op
import sqlalchemy as sa

revision = "q7l8m9n0o1p2"
down_revision = "p6k7l8m9n0o1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Expire all existing pending tokens — they were plaintext and can't
    # be retroactively hashed without the originals. New invites will use
    # hashed storage automatically.
    op.execute(
        sa.text(
            "UPDATE invite_tokens SET expires_at = :now WHERE used_at IS NULL"
        ).bindparams(now=datetime.now(timezone.utc))
    )


def downgrade() -> None:
    pass  # No way to reverse a hash
