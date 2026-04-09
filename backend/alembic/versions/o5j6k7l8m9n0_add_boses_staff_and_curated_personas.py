"""add is_boses_staff to users and curated persona fields to library_personas

Revision ID: o5j6k7l8m9n0
Revises: n4i5j6k7l8m9
Create Date: 2026-04-09 00:00:00.000000

Adds:
- users.is_boses_staff (bool, default False) — platform-level staff flag
- library_personas.is_boses_curated (bool, default False)
- library_personas.research_notes (text, nullable)
- library_personas.source_type (varchar 50, nullable)
"""
import sqlalchemy as sa
from alembic import op

revision = "o5j6k7l8m9n0"
down_revision = "n4i5j6k7l8m9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_boses_staff", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("library_personas", sa.Column("is_boses_curated", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("library_personas", sa.Column("research_notes", sa.Text(), nullable=True))
    op.add_column("library_personas", sa.Column("source_type", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("library_personas", "source_type")
    op.drop_column("library_personas", "research_notes")
    op.drop_column("library_personas", "is_boses_curated")
    op.drop_column("users", "is_boses_staff")
