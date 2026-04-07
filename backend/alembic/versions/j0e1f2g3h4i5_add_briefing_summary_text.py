"""add briefing summary_text

Revision ID: j0e1f2g3h4i5
Revises: i9d0e1f2g3h4
Create Date: 2026-04-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "j0e1f2g3h4i5"
down_revision = "i9d0e1f2g3h4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("briefings", sa.Column("summary_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("briefings", "summary_text")
