"""add_persona_code

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add persona_code as nullable first so we can backfill existing rows
    op.add_column('personas', sa.Column('persona_code', sa.String(8), nullable=True))

    # Backfill: derive code from first 8 hex chars of the UUID (no hyphens, uppercase)
    op.execute(
        "UPDATE personas SET persona_code = SUBSTRING(UPPER(REPLACE(id::text, '-', '')), 1, 8)"
    )

    # Now enforce NOT NULL and UNIQUE
    op.alter_column('personas', 'persona_code', nullable=False)
    op.create_unique_constraint('uq_personas_persona_code', 'personas', ['persona_code'])


def downgrade() -> None:
    op.drop_constraint('uq_personas_persona_code', 'personas', type_='unique')
    op.drop_column('personas', 'persona_code')
