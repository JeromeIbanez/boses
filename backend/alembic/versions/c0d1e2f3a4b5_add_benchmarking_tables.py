"""add benchmarking tables

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-04-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

revision = 'c0d1e2f3a4b5'
down_revision = 'b9c0d1e2f3a4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Reproducibility studies ──────────────────────────────────────────────
    op.create_table(
        'reproducibility_studies',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_simulation_id', UUID(as_uuid=True), sa.ForeignKey('simulations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('n_runs', sa.Integer, nullable=False, server_default='3'),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('sentiment_agreement_rate', sa.Float, nullable=True),
        sa.Column('distribution_variance_score', sa.Float, nullable=True),
        sa.Column('theme_overlap_coefficient', sa.Float, nullable=True),
        sa.Column('confidence_score', sa.Float, nullable=True),
        sa.Column('score_breakdown', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('completed_at', sa.DateTime, nullable=True),
    )

    op.create_table(
        'reproducibility_runs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('study_id', UUID(as_uuid=True), sa.ForeignKey('reproducibility_studies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('simulation_id', UUID(as_uuid=True), sa.ForeignKey('simulations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('run_index', sa.Integer, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )

    # ── Benchmark cases & runs ───────────────────────────────────────────────
    op.create_table(
        'benchmark_cases',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('briefing_text', sa.Text, nullable=False),
        sa.Column('prompt_question', sa.Text, nullable=False),
        sa.Column('simulation_type', sa.String(50), nullable=False, server_default='concept_test'),
        sa.Column('ground_truth', JSONB, nullable=False),
        sa.Column('source_citations', ARRAY(sa.String), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )

    op.create_table(
        'benchmark_runs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('benchmark_case_id', UUID(as_uuid=True), sa.ForeignKey('benchmark_cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('simulation_id', UUID(as_uuid=True), sa.ForeignKey('simulations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('sentiment_accuracy_score', sa.Float, nullable=True),
        sa.Column('distribution_accuracy_score', sa.Float, nullable=True),
        sa.Column('theme_overlap_score', sa.Float, nullable=True),
        sa.Column('overall_accuracy_score', sa.Float, nullable=True),
        sa.Column('score_breakdown', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('completed_at', sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table('benchmark_runs')
    op.drop_table('benchmark_cases')
    op.drop_table('reproducibility_runs')
    op.drop_table('reproducibility_studies')
