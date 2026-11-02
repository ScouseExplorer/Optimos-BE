r"""One-time data migration from SQLite to PostgreSQL for Optimos backend.

Usage (PowerShell):
  .\.venv-2\Scripts\python.exe scripts\migrate_sqlite_to_postgres.py \
    --sqlite-url "sqlite:///./optimos.db" \
    --postgres-url "postgresql://postgres:postgres@localhost:5432/optimos"

Notes:
- Run `alembic upgrade head` against PostgreSQL first.
- By default this script truncates target tables before insert.
- IDs are preserved, then PostgreSQL sequences are advanced.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from typing import Iterable

from sqlalchemy import MetaData, create_engine, inspect, text
from sqlalchemy.engine import Connection, Engine


TABLE_ORDER = [
    "users",
    "feature_costs",
    "subscriptions",
    "user_profiles",
    "notification_preferences",
    "security_settings",
    "credit_wallets",
    "credit_transactions",
    "ai_usage",
    "experiences",
    "opinions",
    "user_posts",
    "chats",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate data from SQLite to PostgreSQL")
    parser.add_argument(
        "--sqlite-url",
        default="sqlite:///./optimos.db",
        help="Source SQLite SQLAlchemy URL",
    )
    parser.add_argument(
        "--postgres-url",
        required=True,
        help="Target PostgreSQL SQLAlchemy URL",
    )
    parser.add_argument(
        "--keep-target-data",
        action="store_true",
        help="Do not truncate target tables before insert",
    )
    return parser.parse_args()


def reflect_tables(engine: Engine, table_names: Iterable[str]) -> MetaData:
    metadata = MetaData()
    metadata.reflect(bind=engine, only=list(table_names))
    return metadata


def truncate_target(pg_conn: Connection, table_names: list[str]) -> None:
    # CASCADE handles FK-linked tables in one pass.
    joined = ", ".join(table_names)
    pg_conn.execute(text(f"TRUNCATE TABLE {joined} RESTART IDENTITY CASCADE"))


def copy_table_rows(sqlite_conn: Connection, pg_conn: Connection, table_name: str) -> int:
    rows = sqlite_conn.execute(text(f"SELECT * FROM {table_name}")).mappings().all()
    if not rows:
        return 0

    pg_columns = inspect(pg_conn).get_columns(table_name)
    column_types = {col["name"]: col["type"].__class__.__name__.lower() for col in pg_columns}

    converted_rows: list[dict] = []
    for row in rows:
        converted: dict = {}
        for key, value in row.items():
            type_name = column_types.get(key, "")

            if value is None:
                converted[key] = None
            elif "bool" in type_name:
                if isinstance(value, str):
                    converted[key] = value.strip().lower() in {"1", "true", "t", "yes", "y"}
                else:
                    converted[key] = bool(value)
            elif "datetime" in type_name or "timestamp" in type_name:
                if isinstance(value, str):
                    converted[key] = datetime.fromisoformat(value)
                else:
                    converted[key] = value
            else:
                converted[key] = value

        converted_rows.append(converted)

    keys = list(rows[0].keys())
    columns_sql = ", ".join(keys)
    values_sql = ", ".join(f":{key}" for key in keys)
    insert_sql = text(f"INSERT INTO {table_name} ({columns_sql}) VALUES ({values_sql})")
    pg_conn.execute(insert_sql, converted_rows)
    return len(converted_rows)


def reset_integer_sequences(pg_conn: Connection, pg_engine: Engine, table_names: list[str]) -> None:
    inspector = inspect(pg_engine)
    for table_name in table_names:
        pk = inspector.get_pk_constraint(table_name)
        pk_columns = pk.get("constrained_columns") or []
        if len(pk_columns) != 1:
            continue

        pk_col = pk_columns[0]
        cols = {col["name"]: col for col in inspector.get_columns(table_name)}
        col = cols.get(pk_col)
        if not col:
            continue

        # Only reset sequence for integer-like PKs.
        col_type_name = col["type"].__class__.__name__.lower()
        if "int" not in col_type_name:
            continue

        seq_name = pg_conn.execute(
            text("SELECT pg_get_serial_sequence(:table_name, :pk_col)"),
            {"table_name": table_name, "pk_col": pk_col},
        ).scalar_one_or_none()

        if not seq_name:
            continue

        max_id = pg_conn.execute(text(f"SELECT COALESCE(MAX({pk_col}), 0) FROM {table_name}")).scalar_one()
        pg_conn.execute(text("SELECT setval(:seq_name, :next_val, true)"), {"seq_name": seq_name, "next_val": max_id})


def main() -> None:
    args = parse_args()

    sqlite_engine = create_engine(args.sqlite_url)
    pg_engine = create_engine(args.postgres_url)

    sqlite_tables = set(inspect(sqlite_engine).get_table_names())
    pg_tables = set(inspect(pg_engine).get_table_names())

    target_tables = [t for t in TABLE_ORDER if t in sqlite_tables and t in pg_tables]
    missing_in_source = [t for t in TABLE_ORDER if t not in sqlite_tables]
    missing_in_target = [t for t in TABLE_ORDER if t not in pg_tables]

    if missing_in_target:
        raise RuntimeError(
            "Target PostgreSQL is missing tables: "
            + ", ".join(missing_in_target)
            + ". Run alembic upgrade head first."
        )

    if not target_tables:
        print("No shared tables found to migrate.")
        return

    if missing_in_source:
        print("Skipping source-missing tables:", ", ".join(missing_in_source))

    with sqlite_engine.connect() as sqlite_conn, pg_engine.begin() as pg_conn:
        if not args.keep_target_data:
            truncate_target(pg_conn, list(reversed(target_tables)))

        total = 0
        for table_name in target_tables:
            count = copy_table_rows(sqlite_conn, pg_conn, table_name)
            total += count
            print(f"Copied {count} row(s) into {table_name}")

        reset_integer_sequences(pg_conn, pg_engine, target_tables)

    print(f"Migration complete. Total rows copied: {total}")


if __name__ == "__main__":
    main()
