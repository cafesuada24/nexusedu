"""Database utilities for cross-dialect support."""

from typing import Any

from sqlalchemy import Insert, Table
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert


def upsert_stmt(
    dialect_name: str,
    table: type[Any] | Table,
    records: list[dict[str, Any]],
    index_elements: list[str],
    update_mapping: dict[str, Any] | None = None,
    update_cols: list[str] | None = None,
) -> Insert:
    """Create a dialect-specific UPSERT statement.

    Args:
        dialect_name: The name of the SQLAlchemy dialect (e.g., 'sqlite', 'postgresql').
        table: The SQLAlchemy model or Table object.
        records: A list of dictionaries representing the records to insert.
        index_elements: The columns that constitute the unique constraint/index.
        update_mapping: A dictionary mapping columns to their new values on conflict.
            If None, 'on_conflict_do_nothing' is used.
        update_cols: A list of column names to update using values from the excluded row.
            Takes precedence over update_mapping if both are provided.

    Returns:
        A SQLAlchemy insert statement with the appropriate 'on_conflict' clause.

    Example:
        >>> stmt = upsert_stmt(
        ...     dialect_name='sqlite',
        ...     table=User,
        ...     records=[{'id': 1, 'name': 'Alice'}],
        ...     index_elements=['id'],
        ...     update_cols=['name']
        ... )
    """
    if dialect_name == 'postgresql':
        stmt = pg_insert(table).values(records)
        if update_cols:
            update_mapping = {col: getattr(stmt.excluded, col) for col in update_cols}

        if update_mapping:
            return stmt.on_conflict_do_update(
                index_elements=index_elements,
                set_=update_mapping,
            )
        return stmt.on_conflict_do_nothing(index_elements=index_elements)

    # Default to SQLite
    stmt = sqlite_insert(table).values(records)
    if update_cols:
        update_mapping = {col: getattr(stmt.excluded, col) for col in update_cols}

    if update_mapping:
        return stmt.on_conflict_do_update(
            index_elements=index_elements,
            set_=update_mapping,
        )
    return stmt.on_conflict_do_nothing(index_elements=index_elements)
