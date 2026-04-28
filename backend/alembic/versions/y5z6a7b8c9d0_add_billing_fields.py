"""add billing fields to companies

Revision ID: y5z6a7b8c9d0
Revises: x4y5z6a7b8c9
Create Date: 2026-04-28

"""
from alembic import op
import sqlalchemy as sa


revision = "y5z6a7b8c9d0"
down_revision = "x4y5z6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("stripe_customer_id", sa.String(255), nullable=True))
    op.add_column("companies", sa.Column("stripe_subscription_id", sa.String(255), nullable=True))
    op.add_column(
        "companies",
        sa.Column("plan", sa.String(50), nullable=False, server_default="free"),
    )
    op.add_column(
        "companies",
        sa.Column("simulations_used", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column(
        "companies",
        sa.Column("billing_period_ends_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_companies_stripe_customer_id", "companies", ["stripe_customer_id"])
    op.create_index("ix_companies_stripe_subscription_id", "companies", ["stripe_subscription_id"])


def downgrade() -> None:
    op.drop_index("ix_companies_stripe_subscription_id", table_name="companies")
    op.drop_index("ix_companies_stripe_customer_id", table_name="companies")
    op.drop_column("companies", "billing_period_ends_at")
    op.drop_column("companies", "simulations_used")
    op.drop_column("companies", "plan")
    op.drop_column("companies", "stripe_subscription_id")
    op.drop_column("companies", "stripe_customer_id")
