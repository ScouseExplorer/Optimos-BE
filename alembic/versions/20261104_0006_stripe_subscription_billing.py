"""add Stripe subscription state and webhook idempotency

Revision ID: 20261104_0006
Revises: 20261102_0005
Create Date: 2026-11-04 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261104_0006"
down_revision: Union[str, Sequence[str], None] = "20261102_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("subscriptions", sa.Column("usage_resets_at", sa.DateTime(), nullable=True))
    op.add_column(
        "subscriptions",
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
    )
    op.execute(
        "UPDATE subscriptions SET usage_resets_at = renews_at "
        "WHERE usage_resets_at IS NULL"
    )
    op.create_index(
        "ix_subscriptions_usage_resets_at",
        "subscriptions",
        ["usage_resets_at"],
        unique=False,
    )
    op.create_index(
        "ix_subscriptions_stripe_subscription_id",
        "subscriptions",
        ["stripe_subscription_id"],
        unique=True,
    )
    op.create_index(
        "ix_subscriptions_stripe_customer_id",
        "subscriptions",
        ["stripe_customer_id"],
        unique=False,
    )
    op.create_table(
        "billing_webhook_receipts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider_event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_billing_webhook_receipts_provider_event_id",
        "billing_webhook_receipts",
        ["provider_event_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_billing_webhook_receipts_provider_event_id",
        table_name="billing_webhook_receipts",
    )
    op.drop_table("billing_webhook_receipts")
    op.drop_index(
        "ix_subscriptions_stripe_customer_id",
        table_name="subscriptions",
    )
    op.drop_index(
        "ix_subscriptions_stripe_subscription_id",
        table_name="subscriptions",
    )
    op.drop_index(
        "ix_subscriptions_usage_resets_at",
        table_name="subscriptions",
    )
    op.drop_column("subscriptions", "stripe_customer_id")
    op.drop_column("subscriptions", "stripe_subscription_id")
    op.drop_column("subscriptions", "usage_resets_at")
