"""add failed_personas to simulations

Revision ID: m3h4i5j6k7l8
Revises: l2g3h4i5j6k7
Create Date: 2026-04-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "m3h4i5j6k7l8"
down_revision = "l2g3h4i5j6k7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "simulations",
        sa.Column("failed_personas", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("simulations", "failed_personas")
