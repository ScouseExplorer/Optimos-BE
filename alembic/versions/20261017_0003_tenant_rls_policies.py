"""enable tenant row-level security policies

Revision ID: 20261017_0003
Revises: 20261017_0002
Create Date: 2026-10-17 00:00:03

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20261017_0003"
down_revision: Union[str, Sequence[str], None] = "20261017_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


USER_ID_TABLES = [
    "user_profiles",
    "notification_preferences",
    "security_settings",
    "subscriptions",
    "credit_wallets",
    "credit_transactions",
    "ai_usage",
    "experiences",
    "opinions",
    "user_posts",
    "chats",
]


ADMIN_OR_OWNER_CONDITION_BY_USER_ID = """
(
    COALESCE(NULLIF(current_setting('app.current_user_is_admin', true), ''), 'false')::boolean
    OR user_id = NULLIF(current_setting('app.current_user_id', true), '')::integer
)
""".strip()

ADMIN_OR_OWNER_CONDITION_BY_ID = """
(
    COALESCE(NULLIF(current_setting('app.current_user_is_admin', true), ''), 'false')::boolean
    OR id = NULLIF(current_setting('app.current_user_id', true), '')::integer
)
""".strip()


def _create_rls_policies() -> None:
    for table in USER_ID_TABLES:
        policy_name = f"tenant_isolation_{table}"
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS {policy_name} ON {table}")
        op.execute(
            f"""
            CREATE POLICY {policy_name} ON {table}
            FOR ALL
            USING ({ADMIN_OR_OWNER_CONDITION_BY_USER_ID})
            WITH CHECK ({ADMIN_OR_OWNER_CONDITION_BY_USER_ID})
            """
        )

    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_users ON users")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation_users ON users
        FOR ALL
        USING ({ADMIN_OR_OWNER_CONDITION_BY_ID})
        WITH CHECK ({ADMIN_OR_OWNER_CONDITION_BY_ID})
        """
    )


def _drop_rls_policies() -> None:
    for table in USER_ID_TABLES:
        policy_name = f"tenant_isolation_{table}"
        op.execute(f"DROP POLICY IF EXISTS {policy_name} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS tenant_isolation_users ON users")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    _create_rls_policies()


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    _drop_rls_policies()
