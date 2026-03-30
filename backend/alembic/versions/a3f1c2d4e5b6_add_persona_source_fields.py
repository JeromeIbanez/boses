"""add_persona_source_fields

Revision ID: a3f1c2d4e5b6
Revises: 684a9adcc09d
Create Date: 2026-03-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a3f1c2d4e5b6'
down_revision: Union[str, None] = '684a9adcc09d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('personas', sa.Column('day_in_the_life', sa.Text(), nullable=True))
    op.add_column('personas', sa.Column('data_source', sa.String(length=50), nullable=False, server_default='synthetic'))
    op.add_column('personas', sa.Column('data_source_references', sa.ARRAY(sa.String()), nullable=True))


def downgrade() -> None:
    op.drop_column('personas', 'data_source_references')
    op.drop_column('personas', 'data_source')
    op.drop_column('personas', 'day_in_the_life')
