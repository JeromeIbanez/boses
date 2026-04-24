"""add prediction_outcomes table

Revision ID: u1v2w3x4y5z6
Revises: t0u1v2w3x4y5
Create Date: 2026-04-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY

revision = "u1v2w3x4y5z6"
down_revision = "t0u1v2w3x4y5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prediction_outcomes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("simulation_id", UUID(as_uuid=True), sa.ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("predicted_sentiment", sa.String(50), nullable=True),
        sa.Column("predicted_themes", ARRAY(sa.String), nullable=True),
        sa.Column("kpi_description", sa.Text, nullable=False),
        sa.Column("outcome_due_date", sa.DateTime, nullable=False),
        sa.Column("actual_outcome_description", sa.Text, nullable=True),
        sa.Column("directional_match", sa.Boolean, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_prediction_outcomes_simulation_id", "prediction_outcomes", ["simulation_id"])
    op.create_index("ix_prediction_outcomes_project_id", "prediction_outcomes", ["project_id"])
    op.create_index("ix_prediction_outcomes_status", "prediction_outcomes", ["status"])


def downgrade() -> None:
    op.drop_index("ix_prediction_outcomes_status", "prediction_outcomes")
    op.drop_index("ix_prediction_outcomes_project_id", "prediction_outcomes")
    op.drop_index("ix_prediction_outcomes_simulation_id", "prediction_outcomes")
    op.drop_table("prediction_outcomes")
