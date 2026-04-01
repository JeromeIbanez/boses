"""fix_fk_ondelete_for_project_deletion

Revision ID: a1b2c3d4e5f6
Revises: f6a7b8c9d0e1
Create Date: 2026-04-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Fix 1: simulations.briefing_id → ON DELETE SET NULL
    # Prevents SQLAlchemy from issuing a redundant UPDATE to NULL when
    # both briefing and simulation are deleted in the same transaction.
    op.drop_constraint('simulations_briefing_id_fkey', 'simulations', type_='foreignkey')
    op.create_foreign_key(
        'fk_simulations_briefing_id', 'simulations', 'briefings',
        ['briefing_id'], ['id'], ondelete='SET NULL',
    )

    # Fix 2: simulations.persona_group_id → ON DELETE CASCADE
    # Allows PostgreSQL to delete simulations automatically when their
    # persona_group is deleted, resolving the topological-sort race.
    op.drop_constraint('simulations_persona_group_id_fkey', 'simulations', type_='foreignkey')
    op.create_foreign_key(
        'fk_simulations_persona_group_id', 'simulations', 'persona_groups',
        ['persona_group_id'], ['id'], ondelete='CASCADE',
    )

    # Fix 3: simulation_results.persona_id → ON DELETE SET NULL
    # Removes the need for Persona.simulation_results cascade="delete-orphan"
    # which caused double-delete when both Simulation and Persona were deleted
    # in the same transaction.
    op.drop_constraint('simulation_results_persona_id_fkey', 'simulation_results', type_='foreignkey')
    op.create_foreign_key(
        'fk_simulation_results_persona_id', 'simulation_results', 'personas',
        ['persona_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_simulation_results_persona_id', 'simulation_results', type_='foreignkey')
    op.create_foreign_key(
        'simulation_results_persona_id_fkey', 'simulation_results', 'personas',
        ['persona_id'], ['id'],
    )

    op.drop_constraint('fk_simulations_persona_group_id', 'simulations', type_='foreignkey')
    op.create_foreign_key(
        'simulations_persona_group_id_fkey', 'simulations', 'persona_groups',
        ['persona_group_id'], ['id'],
    )

    op.drop_constraint('fk_simulations_briefing_id', 'simulations', type_='foreignkey')
    op.create_foreign_key(
        'simulations_briefing_id_fkey', 'simulations', 'briefings',
        ['briefing_id'], ['id'],
    )
