"""enforce unique billing purchase references per user

Revision ID: 20261020_0004
Revises: 20261017_0003
Create Date: 2026-10-20 00:00:04

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20261020_0004"
down_revision: Union[str, Sequence[str], None] = "20261017_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEX_NAME = "uq_credit_tx_billing_purchase_ref"


def upgrade() -> None:
    op.create_index(
        INDEX_NAME,
        "credit_transactions",
        ["user_id", "reference_id"],
        unique=True,
        postgresql_where=sa.text("transaction_type = 'BILLING_PURCHASE' AND reference_id IS NOT NULL"),
        sqlite_where=sa.text("transaction_type = 'BILLING_PURCHASE' AND reference_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="credit_transactions")
