"""research_grade_persona_fields

Revision ID: t0u1v2w3x4y5
Revises: s9t0u1v2w3x4
Create Date: 2026-04-24

Adds:
  - personas.dominant_brand_stance   VARCHAR(50)  — carried from Pass 1 skeleton
  - personas.ocean_profile           JSONB        — Big Five personality scores
  - persona_groups.generation_metadata JSONB      — audit trail for each generation run
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 't0u1v2w3x4y5'
down_revision: str = 's9t0u1v2w3x4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('personas', sa.Column('dominant_brand_stance', sa.String(50), nullable=True))
    op.add_column('personas', sa.Column('ocean_profile', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('persona_groups', sa.Column('generation_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('persona_groups', 'generation_metadata')
    op.drop_column('personas', 'ocean_profile')
    op.drop_column('personas', 'dominant_brand_stance')
