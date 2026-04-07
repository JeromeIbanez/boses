"""add simulation_briefings junction table

Revision ID: i9d0e1f2g3h4
Revises: h8c9d0e1f2g3
Create Date: 2026-04-07

"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'i9d0e1f2g3h4'
down_revision = 'h8c9d0e1f2g3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create junction table
    op.create_table(
        'simulation_briefings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('simulation_id', UUID(as_uuid=True),
                  sa.ForeignKey('simulations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('briefing_id', UUID(as_uuid=True),
                  sa.ForeignKey('briefings.id', ondelete='CASCADE'), nullable=False),
        sa.UniqueConstraint('simulation_id', 'briefing_id'),
    )

    # 2. Migrate existing single briefing_id rows → junction rows
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, briefing_id FROM simulations WHERE briefing_id IS NOT NULL")
    ).fetchall()
    if rows:
        conn.execute(
            sa.text(
                "INSERT INTO simulation_briefings (id, simulation_id, briefing_id) "
                "VALUES (:id, :simulation_id, :briefing_id)"
            ),
            [{"id": str(uuid.uuid4()), "simulation_id": str(r[0]), "briefing_id": str(r[1])} for r in rows],
        )

    # 3. Drop old FK constraint and column
    op.drop_constraint('fk_simulations_briefing_id', 'simulations', type_='foreignkey')
    op.drop_column('simulations', 'briefing_id')


def downgrade() -> None:
    # Re-add briefing_id column
    op.add_column('simulations', sa.Column('briefing_id', UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'simulations_briefing_id_fkey', 'simulations', 'briefings',
        ['briefing_id'], ['id'], ondelete='SET NULL',
    )

    # Backfill from junction table (take first briefing per simulation)
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE simulations s
        SET briefing_id = sb.briefing_id
        FROM (
            SELECT DISTINCT ON (simulation_id) simulation_id, briefing_id
            FROM simulation_briefings
            ORDER BY simulation_id
        ) sb
        WHERE s.id = sb.simulation_id
    """))

    op.drop_table('simulation_briefings')
