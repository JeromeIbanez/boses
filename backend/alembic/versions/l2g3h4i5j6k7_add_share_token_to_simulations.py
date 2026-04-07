"""add share_token to simulations

Revision ID: l2g3h4i5j6k7
Revises: k1f2g3h4i5j6
Create Date: 2026-04-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "l2g3h4i5j6k7"
down_revision = "k1f2g3h4i5j6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "simulations",
        sa.Column("share_token", sa.String(64), nullable=True, unique=True),
    )
    op.create_index("ix_simulations_share_token", "simulations", ["share_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_simulations_share_token", table_name="simulations")
    op.drop_column("simulations", "share_token")
