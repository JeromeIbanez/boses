"""add persona generation progress

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-04-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'b9c0d1e2f3a4'
down_revision = 'a8b9c0d1e2f3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('persona_groups', sa.Column('generation_progress', JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column('persona_groups', 'generation_progress')
