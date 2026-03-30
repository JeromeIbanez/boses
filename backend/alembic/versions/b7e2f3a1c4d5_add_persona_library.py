"""add_persona_library

Revision ID: b7e2f3a1c4d5
Revises: a3f1c2d4e5b6
Create Date: 2026-03-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY

revision = "b7e2f3a1c4d5"
down_revision = "a3f1c2d4e5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create library_personas table (global NPC store)
    op.create_table(
        "library_personas",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("age", sa.Integer, nullable=False),
        sa.Column("gender", sa.String(50), nullable=False),
        sa.Column("location", sa.String(255), nullable=False),
        sa.Column("occupation", sa.String(255), nullable=False),
        sa.Column("income_level", sa.String(100), nullable=False),
        sa.Column("educational_background", sa.Text, nullable=True),
        sa.Column("family_situation", sa.Text, nullable=True),
        sa.Column("background", sa.Text, nullable=True),
        sa.Column("personality_traits", ARRAY(sa.Text), nullable=True),
        sa.Column("goals", sa.Text, nullable=True),
        sa.Column("pain_points", sa.Text, nullable=True),
        sa.Column("tech_savviness", sa.String(100), nullable=True),
        sa.Column("media_consumption", sa.Text, nullable=True),
        sa.Column("spending_habits", sa.Text, nullable=True),
        sa.Column("day_in_the_life", sa.Text, nullable=True),
        sa.Column("data_source", sa.String(50), nullable=False, server_default="synthetic"),
        sa.Column("data_source_references", ARRAY(sa.Text), nullable=True),
        sa.Column("simulation_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_retired", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # 2. Create persona_library_links junction table
    op.create_table(
        "persona_library_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("persona_id", UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("library_persona_id", UUID(as_uuid=True), sa.ForeignKey("library_personas.id"), nullable=False),
        sa.Column("match_score", sa.Float, nullable=True),  # NULL = freshly generated, not matched
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # 3. Add library_persona_id FK to personas (denormalized shortcut for badging)
    op.add_column(
        "personas",
        sa.Column("library_persona_id", UUID(as_uuid=True), sa.ForeignKey("library_personas.id"), nullable=True),
    )

    # Indexes
    op.create_index("ix_library_personas_location", "library_personas", ["location"])
    op.create_index("ix_library_personas_gender", "library_personas", ["gender"])
    op.create_index("ix_library_personas_income_level", "library_personas", ["income_level"])
    op.create_index("ix_library_personas_age", "library_personas", ["age"])
    op.create_index("ix_library_personas_is_retired", "library_personas", ["is_retired"])
    op.create_index("ix_persona_library_links_library_persona_id", "persona_library_links", ["library_persona_id"])


def downgrade() -> None:
    op.drop_index("ix_persona_library_links_library_persona_id", table_name="persona_library_links")
    op.drop_index("ix_library_personas_is_retired", table_name="library_personas")
    op.drop_index("ix_library_personas_age", table_name="library_personas")
    op.drop_index("ix_library_personas_income_level", table_name="library_personas")
    op.drop_index("ix_library_personas_gender", table_name="library_personas")
    op.drop_index("ix_library_personas_location", table_name="library_personas")
    op.drop_column("personas", "library_persona_id")
    op.drop_table("persona_library_links")
    op.drop_table("library_personas")
