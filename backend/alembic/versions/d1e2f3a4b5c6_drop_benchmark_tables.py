"""drop benchmark tables

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
Create Date: 2026-04-02

"""
from alembic import op

revision = 'd1e2f3a4b5c6'
down_revision = 'c0d1e2f3a4b5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table('benchmark_runs')
    op.drop_table('benchmark_cases')


def downgrade() -> None:
    pass  # benchmark feature removed intentionally
