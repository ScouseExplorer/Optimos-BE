"""add global dataset items table

Revision ID: 20261017_0002
Revises: 20260922_0001
Create Date: 2026-10-17 00:00:02

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20261017_0002"
down_revision: Union[str, Sequence[str], None] = "20260922_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "global_dataset_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_key", sa.String(length=100), nullable=False),
        sa.Column("item_key", sa.String(length=150), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_key", "item_key", name="uq_global_dataset_item_dataset_item"),
    )
    op.create_index("ix_global_dataset_items_id", "global_dataset_items", ["id"], unique=False)
    op.create_index("ix_global_dataset_items_dataset_key", "global_dataset_items", ["dataset_key"], unique=False)
    op.create_index("ix_global_dataset_items_item_key", "global_dataset_items", ["item_key"], unique=False)
    op.create_index("ix_global_dataset_items_priority", "global_dataset_items", ["priority"], unique=False)
    op.create_index("ix_global_dataset_items_is_active", "global_dataset_items", ["is_active"], unique=False)
    op.create_index("ix_global_dataset_items_created_at", "global_dataset_items", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_global_dataset_items_created_at", table_name="global_dataset_items")
    op.drop_index("ix_global_dataset_items_is_active", table_name="global_dataset_items")
    op.drop_index("ix_global_dataset_items_priority", table_name="global_dataset_items")
    op.drop_index("ix_global_dataset_items_item_key", table_name="global_dataset_items")
    op.drop_index("ix_global_dataset_items_dataset_key", table_name="global_dataset_items")
    op.drop_index("ix_global_dataset_items_id", table_name="global_dataset_items")
    op.drop_table("global_dataset_items")
