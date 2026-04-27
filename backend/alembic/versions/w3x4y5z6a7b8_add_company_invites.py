"""add company_invites table

Revision ID: w3x4y5z6a7b8
Revises: v2w3x4y5z6a7
Create Date: 2026-04-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "w3x4y5z6a7b8"
down_revision = "v2w3x4y5z6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company_invites",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invited_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="member"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_company_invites_company_id", "company_invites", ["company_id"])
    op.create_index("ix_company_invites_email", "company_invites", ["email"])
    op.create_unique_constraint("uq_company_invites_token_hash", "company_invites", ["token_hash"])
    op.create_index("ix_company_invites_token_hash", "company_invites", ["token_hash"])


def downgrade() -> None:
    op.drop_index("ix_company_invites_token_hash", table_name="company_invites")
    op.drop_constraint("uq_company_invites_token_hash", "company_invites", type_="unique")
    op.drop_index("ix_company_invites_email", table_name="company_invites")
    op.drop_index("ix_company_invites_company_id", table_name="company_invites")
    op.drop_table("company_invites")
