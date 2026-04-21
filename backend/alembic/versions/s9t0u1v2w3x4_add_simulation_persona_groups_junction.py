"""add simulation_persona_groups junction table

Revision ID: s9t0u1v2w3x4
Revises: r8m9n0o1p2q3
Create Date: 2026-04-21

"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 's9t0u1v2w3x4'
down_revision = 'r8m9n0o1p2q3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create junction table
    op.create_table(
        'simulation_persona_groups',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('simulation_id', UUID(as_uuid=True),
                  sa.ForeignKey('simulations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('persona_group_id', UUID(as_uuid=True),
                  sa.ForeignKey('persona_groups.id', ondelete='CASCADE'), nullable=False),
        sa.UniqueConstraint('simulation_id', 'persona_group_id'),
    )
    op.create_index('ix_spg_simulation_id', 'simulation_persona_groups', ['simulation_id'])
    op.create_index('ix_spg_persona_group_id', 'simulation_persona_groups', ['persona_group_id'])

    # 2. Backfill from existing persona_group_id on simulations
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, persona_group_id FROM simulations WHERE persona_group_id IS NOT NULL")
    ).fetchall()
    if rows:
        conn.execute(
            sa.text(
                "INSERT INTO simulation_persona_groups (id, simulation_id, persona_group_id) "
                "VALUES (:id, :simulation_id, :persona_group_id)"
            ),
            [{"id": str(uuid.uuid4()), "simulation_id": str(r[0]), "persona_group_id": str(r[1])} for r in rows],
        )

    # 3. Make persona_group_id nullable and change FK to SET NULL (not CASCADE)
    op.drop_constraint('fk_simulations_persona_group_id', 'simulations', type_='foreignkey')
    op.alter_column('simulations', 'persona_group_id', nullable=True)
    op.create_foreign_key(
        'fk_simulations_persona_group_id',
        'simulations', 'persona_groups',
        ['persona_group_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    # Restore NOT NULL + CASCADE on persona_group_id
    # First backfill from junction table (first group per simulation)
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE simulations s
        SET persona_group_id = spg.persona_group_id
        FROM (
            SELECT DISTINCT ON (simulation_id) simulation_id, persona_group_id
            FROM simulation_persona_groups
            ORDER BY simulation_id
        ) spg
        WHERE s.id = spg.simulation_id AND s.persona_group_id IS NULL
    """))

    op.drop_constraint('fk_simulations_persona_group_id', 'simulations', type_='foreignkey')
    op.alter_column('simulations', 'persona_group_id', nullable=False)
    op.create_foreign_key(
        'fk_simulations_persona_group_id',
        'simulations', 'persona_groups',
        ['persona_group_id'], ['id'],
        ondelete='CASCADE',
    )

    op.drop_index('ix_spg_persona_group_id', 'simulation_persona_groups')
    op.drop_index('ix_spg_simulation_id', 'simulation_persona_groups')
    op.drop_table('simulation_persona_groups')
