"""enrich persona fields

Revision ID: a8b9c0d1e2f3
Revises: f6a7b8c9d0e1
Create Date: 2026-04-02

Adds 6 new marketing-segmentation columns to personas and library_personas:
  archetype_label, psychographic_segment, brand_attitudes,
  buying_triggers, aspirational_identity, digital_behavior
"""
from alembic import op
import sqlalchemy as sa

revision = 'a8b9c0d1e2f3'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    str_cols = ["archetype_label", "psychographic_segment"]
    text_cols = ["brand_attitudes", "buying_triggers", "aspirational_identity", "digital_behavior"]

    for table in ("personas", "library_personas"):
        for col in str_cols:
            op.add_column(table, sa.Column(col, sa.String(100), nullable=True))
        for col in text_cols:
            op.add_column(table, sa.Column(col, sa.Text, nullable=True))


def downgrade() -> None:
    cols = [
        "archetype_label", "psychographic_segment",
        "brand_attitudes", "buying_triggers", "aspirational_identity", "digital_behavior",
    ]
    for table in ("personas", "library_personas"):
        for col in cols:
            op.drop_column(table, col)
