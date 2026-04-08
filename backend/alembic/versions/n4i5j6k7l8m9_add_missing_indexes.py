"""add missing indexes for performance

Revision ID: n4i5j6k7l8m9
Revises: m3h4i5j6k7l8
Create Date: 2026-04-08 00:00:00.000000

Adds indexes on high-traffic foreign key and filter columns that were missing,
causing full table scans on every simulation run and result fetch.
"""
from alembic import op


def upgrade() -> None:
    # simulation_results.simulation_id — every result fetch for a simulation
    op.create_index(
        "ix_simulation_results_simulation_id",
        "simulation_results",
        ["simulation_id"],
    )
    # simulation_results.created_at — chronological ordering
    op.create_index(
        "ix_simulation_results_created_at",
        "simulation_results",
        ["created_at"],
    )
    # personas.persona_group_id — loaded on every simulation run
    op.create_index(
        "ix_personas_persona_group_id",
        "personas",
        ["persona_group_id"],
    )
    # simulations.project_id — listing simulations per project
    op.create_index(
        "ix_simulations_project_id",
        "simulations",
        ["project_id"],
    )
    # simulations.status — convergence/reliability queries filter by status
    op.create_index(
        "ix_simulations_status",
        "simulations",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_simulations_status", table_name="simulations")
    op.drop_index("ix_simulations_project_id", table_name="simulations")
    op.drop_index("ix_personas_persona_group_id", table_name="personas")
    op.drop_index("ix_simulation_results_created_at", table_name="simulation_results")
    op.drop_index("ix_simulation_results_simulation_id", table_name="simulation_results")
