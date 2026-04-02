"""add persona avatar_url

Revision ID: g7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-04-02

"""
from alembic import op
import sqlalchemy as sa

revision = 'g7b8c9d0e1f2'
down_revision = ('f6a7b8c9d0e1', 'e2f3a4b5c6d7')
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('personas', sa.Column('avatar_url', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('personas', 'avatar_url')
