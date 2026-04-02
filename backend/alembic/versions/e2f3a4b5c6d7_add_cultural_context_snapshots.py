"""add cultural context snapshots

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-04-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = 'e2f3a4b5c6d7'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'cultural_context_snapshots',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('market_code', sa.String(5), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('signals_json', JSONB, nullable=True),
        sa.Column('raw_sources', JSONB, nullable=True),
        sa.Column('quality_score', sa.Float, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('activated_at', sa.DateTime, nullable=True),
    )
    op.create_index('ix_cultural_context_snapshots_market_code', 'cultural_context_snapshots', ['market_code'])


def downgrade() -> None:
    op.drop_index('ix_cultural_context_snapshots_market_code', table_name='cultural_context_snapshots')
    op.drop_table('cultural_context_snapshots')
