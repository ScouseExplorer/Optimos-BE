"""initial backend schema

Revision ID: 20260922_0001
Revises: 
Create Date: 2026-09-22 00:00:01

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260922_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feature_costs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("feature_key", sa.String(length=128), nullable=False),
        sa.Column("credit_cost", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feature_key"),
    )
    op.create_index("ix_feature_costs_id", "feature_costs", ["id"], unique=False)
    op.create_index("ix_feature_costs_feature_key", "feature_costs", ["feature_key"], unique=False)
    op.create_index("ix_feature_costs_created_at", "feature_costs", ["created_at"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_users_username", "users", ["username"], unique=False)
    op.create_index("ix_users_created_at", "users", ["created_at"], unique=False)

    op.create_table(
        "ai_usage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Float(), nullable=True),
        sa.Column("credits_charged", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_usage_id", "ai_usage", ["id"], unique=False)
    op.create_index("ix_ai_usage_user_id", "ai_usage", ["user_id"], unique=False)
    op.create_index("ix_ai_usage_action", "ai_usage", ["action"], unique=False)
    op.create_index("ix_ai_usage_request_id", "ai_usage", ["request_id"], unique=False)
    op.create_index("ix_ai_usage_status", "ai_usage", ["status"], unique=False)
    op.create_index("ix_ai_usage_created_at", "ai_usage", ["created_at"], unique=False)

    op.create_table(
        "credit_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("transaction_type", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("reference_id", sa.String(length=128), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "request_id", "transaction_type", name="uq_credit_tx_user_request_type"),
    )
    op.create_index("ix_credit_transactions_id", "credit_transactions", ["id"], unique=False)
    op.create_index("ix_credit_transactions_user_id", "credit_transactions", ["user_id"], unique=False)
    op.create_index("ix_credit_transactions_transaction_type", "credit_transactions", ["transaction_type"], unique=False)
    op.create_index("ix_credit_transactions_source", "credit_transactions", ["source"], unique=False)
    op.create_index("ix_credit_transactions_reference_id", "credit_transactions", ["reference_id"], unique=False)
    op.create_index("ix_credit_transactions_request_id", "credit_transactions", ["request_id"], unique=False)
    op.create_index("ix_credit_transactions_status", "credit_transactions", ["status"], unique=False)
    op.create_index("ix_credit_transactions_created_at", "credit_transactions", ["created_at"], unique=False)

    op.create_table(
        "credit_wallets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("balance", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_credit_wallets_id", "credit_wallets", ["id"], unique=False)
    op.create_index("ix_credit_wallets_user_id", "credit_wallets", ["user_id"], unique=False)
    op.create_index("ix_credit_wallets_created_at", "credit_wallets", ["created_at"], unique=False)

    op.create_table(
        "experiences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("experience_date", sa.DateTime(), nullable=True),
        sa.Column("importance", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_experiences_id", "experiences", ["id"], unique=False)
    op.create_index("ix_experiences_user_id", "experiences", ["user_id"], unique=False)
    op.create_index("ix_experiences_category", "experiences", ["category"], unique=False)
    op.create_index("ix_experiences_created_at", "experiences", ["created_at"], unique=False)

    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("email_new_message", sa.Boolean(), nullable=False),
        sa.Column("email_billing", sa.Boolean(), nullable=False),
        sa.Column("email_security", sa.Boolean(), nullable=False),
        sa.Column("email_product_updates", sa.Boolean(), nullable=False),
        sa.Column("email_weekly_summary", sa.Boolean(), nullable=False),
        sa.Column("push_enabled", sa.Boolean(), nullable=False),
        sa.Column("push_new_message", sa.Boolean(), nullable=False),
        sa.Column("push_billing", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_notification_preferences_id", "notification_preferences", ["id"], unique=False)
    op.create_index("ix_notification_preferences_user_id", "notification_preferences", ["user_id"], unique=False)
    op.create_index("ix_notification_preferences_created_at", "notification_preferences", ["created_at"], unique=False)

    op.create_table(
        "opinions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(length=200), nullable=False),
        sa.Column("opinion", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_opinions_id", "opinions", ["id"], unique=False)
    op.create_index("ix_opinions_user_id", "opinions", ["user_id"], unique=False)
    op.create_index("ix_opinions_topic", "opinions", ["topic"], unique=False)
    op.create_index("ix_opinions_created_at", "opinions", ["created_at"], unique=False)

    op.create_table(
        "security_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("two_factor_enabled", sa.Boolean(), nullable=False),
        sa.Column("two_factor_method", sa.String(length=20), nullable=True),
        sa.Column("two_factor_secret", sa.String(length=255), nullable=True),
        sa.Column("session_timeout_minutes", sa.Integer(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("last_login_ip", sa.String(length=45), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(), nullable=False),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_security_settings_id", "security_settings", ["id"], unique=False)
    op.create_index("ix_security_settings_user_id", "security_settings", ["user_id"], unique=False)
    op.create_index("ix_security_settings_created_at", "security_settings", ["created_at"], unique=False)

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tier", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("messages_limit", sa.Integer(), nullable=True),
        sa.Column("messages_used", sa.Integer(), nullable=True),
        sa.Column("renews_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_subscriptions_id", "subscriptions", ["id"], unique=False)
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=False)
    op.create_index("ix_subscriptions_tier", "subscriptions", ["tier"], unique=False)
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"], unique=False)
    op.create_index("ix_subscriptions_renews_at", "subscriptions", ["renews_at"], unique=False)
    op.create_index("ix_subscriptions_created_at", "subscriptions", ["created_at"], unique=False)

    op.create_table(
        "user_posts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("linkedin_post_id", sa.String(length=128), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("posted_at", sa.DateTime(), nullable=True),
        sa.Column("impressions", sa.Integer(), nullable=True),
        sa.Column("likes", sa.Integer(), nullable=True),
        sa.Column("comments", sa.Integer(), nullable=True),
        sa.Column("reposts", sa.Integer(), nullable=True),
        sa.Column("engagement_rate", sa.Float(), nullable=True),
        sa.Column("topic", sa.String(length=100), nullable=True),
        sa.Column("post_format", sa.String(length=100), nullable=True),
        sa.Column("hook_type", sa.String(length=100), nullable=True),
        sa.Column("media_type", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_posts_id", "user_posts", ["id"], unique=False)
    op.create_index("ix_user_posts_user_id", "user_posts", ["user_id"], unique=False)
    op.create_index("ix_user_posts_linkedin_post_id", "user_posts", ["linkedin_post_id"], unique=False)
    op.create_index("ix_user_posts_topic", "user_posts", ["topic"], unique=False)
    op.create_index("ix_user_posts_post_format", "user_posts", ["post_format"], unique=False)
    op.create_index("ix_user_posts_created_at", "user_posts", ["created_at"], unique=False)

    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("display_name", sa.String(length=150), nullable=True),
        sa.Column("bio", sa.String(length=500), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("timezone", sa.String(length=50), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_user_profiles_id", "user_profiles", ["id"], unique=False)
    op.create_index("ix_user_profiles_user_id", "user_profiles", ["user_id"], unique=False)
    op.create_index("ix_user_profiles_created_at", "user_profiles", ["created_at"], unique=False)

    op.create_table(
        "chats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("user_message", sa.Text(), nullable=False),
        sa.Column("ai_response", sa.Text(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chats_id", "chats", ["id"], unique=False)
    op.create_index("ix_chats_user_id", "chats", ["user_id"], unique=False)
    op.create_index("ix_chats_subscription_id", "chats", ["subscription_id"], unique=False)
    op.create_index("ix_chats_request_id", "chats", ["request_id"], unique=False)
    op.create_index("ix_chats_created_at", "chats", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_chats_created_at", table_name="chats")
    op.drop_index("ix_chats_request_id", table_name="chats")
    op.drop_index("ix_chats_subscription_id", table_name="chats")
    op.drop_index("ix_chats_user_id", table_name="chats")
    op.drop_index("ix_chats_id", table_name="chats")
    op.drop_table("chats")

    op.drop_index("ix_user_profiles_created_at", table_name="user_profiles")
    op.drop_index("ix_user_profiles_user_id", table_name="user_profiles")
    op.drop_index("ix_user_profiles_id", table_name="user_profiles")
    op.drop_table("user_profiles")

    op.drop_index("ix_user_posts_created_at", table_name="user_posts")
    op.drop_index("ix_user_posts_post_format", table_name="user_posts")
    op.drop_index("ix_user_posts_topic", table_name="user_posts")
    op.drop_index("ix_user_posts_linkedin_post_id", table_name="user_posts")
    op.drop_index("ix_user_posts_user_id", table_name="user_posts")
    op.drop_index("ix_user_posts_id", table_name="user_posts")
    op.drop_table("user_posts")

    op.drop_index("ix_subscriptions_created_at", table_name="subscriptions")
    op.drop_index("ix_subscriptions_renews_at", table_name="subscriptions")
    op.drop_index("ix_subscriptions_status", table_name="subscriptions")
    op.drop_index("ix_subscriptions_tier", table_name="subscriptions")
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_id", table_name="subscriptions")
    op.drop_table("subscriptions")

    op.drop_index("ix_security_settings_created_at", table_name="security_settings")
    op.drop_index("ix_security_settings_user_id", table_name="security_settings")
    op.drop_index("ix_security_settings_id", table_name="security_settings")
    op.drop_table("security_settings")

    op.drop_index("ix_opinions_created_at", table_name="opinions")
    op.drop_index("ix_opinions_topic", table_name="opinions")
    op.drop_index("ix_opinions_user_id", table_name="opinions")
    op.drop_index("ix_opinions_id", table_name="opinions")
    op.drop_table("opinions")

    op.drop_index("ix_notification_preferences_created_at", table_name="notification_preferences")
    op.drop_index("ix_notification_preferences_user_id", table_name="notification_preferences")
    op.drop_index("ix_notification_preferences_id", table_name="notification_preferences")
    op.drop_table("notification_preferences")

    op.drop_index("ix_experiences_created_at", table_name="experiences")
    op.drop_index("ix_experiences_category", table_name="experiences")
    op.drop_index("ix_experiences_user_id", table_name="experiences")
    op.drop_index("ix_experiences_id", table_name="experiences")
    op.drop_table("experiences")

    op.drop_index("ix_credit_wallets_created_at", table_name="credit_wallets")
    op.drop_index("ix_credit_wallets_user_id", table_name="credit_wallets")
    op.drop_index("ix_credit_wallets_id", table_name="credit_wallets")
    op.drop_table("credit_wallets")

    op.drop_index("ix_credit_transactions_created_at", table_name="credit_transactions")
    op.drop_index("ix_credit_transactions_status", table_name="credit_transactions")
    op.drop_index("ix_credit_transactions_request_id", table_name="credit_transactions")
    op.drop_index("ix_credit_transactions_reference_id", table_name="credit_transactions")
    op.drop_index("ix_credit_transactions_source", table_name="credit_transactions")
    op.drop_index("ix_credit_transactions_transaction_type", table_name="credit_transactions")
    op.drop_index("ix_credit_transactions_user_id", table_name="credit_transactions")
    op.drop_index("ix_credit_transactions_id", table_name="credit_transactions")
    op.drop_table("credit_transactions")

    op.drop_index("ix_ai_usage_created_at", table_name="ai_usage")
    op.drop_index("ix_ai_usage_status", table_name="ai_usage")
    op.drop_index("ix_ai_usage_request_id", table_name="ai_usage")
    op.drop_index("ix_ai_usage_action", table_name="ai_usage")
    op.drop_index("ix_ai_usage_user_id", table_name="ai_usage")
    op.drop_index("ix_ai_usage_id", table_name="ai_usage")
    op.drop_table("ai_usage")

    op.drop_index("ix_users_created_at", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_feature_costs_created_at", table_name="feature_costs")
    op.drop_index("ix_feature_costs_feature_key", table_name="feature_costs")
    op.drop_index("ix_feature_costs_id", table_name="feature_costs")
    op.drop_table("feature_costs")
