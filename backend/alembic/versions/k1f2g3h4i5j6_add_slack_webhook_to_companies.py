"""add slack_webhook_url to companies

Revision ID: k1f2g3h4i5j6
Revises: j0e1f2g3h4i5
Create Date: 2026-04-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "k1f2g3h4i5j6"
down_revision = "j0e1f2g3h4i5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("slack_webhook_url", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("companies", "slack_webhook_url")
