"""make_prompt_question_nullable

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('simulations', 'prompt_question', nullable=True)


def downgrade() -> None:
    op.alter_column('simulations', 'prompt_question', nullable=False)
