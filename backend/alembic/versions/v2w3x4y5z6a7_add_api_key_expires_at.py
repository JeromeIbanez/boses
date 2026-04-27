"""add expires_at to api_keys

Revision ID: v2w3x4y5z6a7
Revises: u1v2w3x4y5z6
Create Date: 2026-04-26
"""

from alembic import op
import sqlalchemy as sa

revision = "v2w3x4y5z6a7"
down_revision = "ffe5c79d10ba"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "api_keys",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("api_keys", "expires_at")
