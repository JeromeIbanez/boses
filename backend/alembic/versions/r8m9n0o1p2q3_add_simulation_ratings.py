"""add simulation_ratings table

Revision ID: r8m9n0o1p2q3
Revises: q7l8m9n0o1p2
Create Date: 2026-04-15 00:00:00.000000

The SimulationRating model was added to the codebase without a corresponding
migration, causing a missing-table error at runtime whenever the ORM lazy-loaded
the `ratings` relationship on a Simulation (e.g. on project DELETE).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "r8m9n0o1p2q3"
down_revision = "q7l8m9n0o1p2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "simulation_ratings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "simulation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("simulations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_simulation_ratings_simulation_id",
        "simulation_ratings",
        ["simulation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_simulation_ratings_simulation_id", table_name="simulation_ratings")
    op.drop_table("simulation_ratings")
