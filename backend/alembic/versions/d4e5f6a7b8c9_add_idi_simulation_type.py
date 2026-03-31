"""add_idi_simulation_type

Revision ID: d4e5f6a7b8c9
Revises: c1d2e3f4a5b6
Create Date: 2026-03-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # simulations: add simulation_type, make briefing_id optional, add IDI fields
    op.add_column('simulations', sa.Column('simulation_type', sa.String(50), nullable=False, server_default='concept_test'))
    op.add_column('simulations', sa.Column('idi_script_text', sa.Text(), nullable=True))
    op.add_column('simulations', sa.Column('idi_persona_id', sa.UUID(), nullable=True))
    op.alter_column('simulations', 'briefing_id', nullable=True)
    op.create_foreign_key(
        'fk_simulations_idi_persona_id',
        'simulations', 'personas',
        ['idi_persona_id'], ['id'],
        ondelete='SET NULL',
    )

    # simulation_results: add IDI result fields
    op.add_column('simulation_results', sa.Column('transcript', sa.Text(), nullable=True))
    op.add_column('simulation_results', sa.Column('report_sections', postgresql.JSONB(), nullable=True))

    # new idi_messages table
    op.create_table(
        'idi_messages',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('simulation_id', sa.UUID(), sa.ForeignKey('simulations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('persona_id', sa.UUID(), sa.ForeignKey('personas.id', ondelete='SET NULL'), nullable=True),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_idi_messages_simulation_id', 'idi_messages', ['simulation_id'])


def downgrade() -> None:
    op.drop_index('ix_idi_messages_simulation_id', 'idi_messages')
    op.drop_table('idi_messages')
    op.drop_column('simulation_results', 'report_sections')
    op.drop_column('simulation_results', 'transcript')
    op.drop_constraint('fk_simulations_idi_persona_id', 'simulations', type_='foreignkey')
    op.alter_column('simulations', 'briefing_id', nullable=False)
    op.drop_column('simulations', 'idi_persona_id')
    op.drop_column('simulations', 'idi_script_text')
    op.drop_column('simulations', 'simulation_type')
