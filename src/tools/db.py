"""Tools for multi-source DB access.

Provides a universal interface for the LLM Agent to discover,
inspect, and query multiple database sources (LMS, SIS) via DuckDB.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.database import DB_REGISTRY

if TYPE_CHECKING:
    from src.database.manager import DatabaseManager

# ============================================================================
# DATABASE TOOLS
# ============================================================================


def get_db_list() -> str:
    """Retrieve list of available databases."""
    header = '## AVAILABLE DATABASE REGISTRY\n'
    entries = []
    for db in DB_REGISTRY:
        entry = f'### ID: `{db["id"]}`\n- **Description**: {db["description"]}\n- **Keywords**: {", ".join(db["keywords"])}\n'
        entries.append(entry)
    return header + '\n---\n'.join(entries)


def list_tables(db_id: str, db_manager: DatabaseManager) -> str:
    """List all tables available in the specified database."""
    try:
        tables = db_manager.list_tables(db_id)
        return f'## Tables in {db_id}:' + '\n- '.join(tables)
    except Exception as e:
        return f'Error: {e}'


def describe_table(db_id: str, table_name: str, db_manager: DatabaseManager) -> str:
    """Get the detailed schema and sample data for a specific table."""
    try:
        return db_manager.get_table_schema(db_id, table_name)
    except Exception as e:
        return f'Error: {e}'


def get_db_schema(db_id: str, db_manager: DatabaseManager) -> str:
    """Get the detailed schema of a specific database."""
    try:
        tables = db_manager.list_tables(db_id)
        schemas = [db_manager.get_table_schema(db_id, t) for t in tables]
        return f'### DATABASE: {db_id.upper()}\n' + '\n\n'.join(schemas)
    except Exception as e:
        return f'Error: {e}'


def execute_sql(db_id: str, sql: str, db_manager: DatabaseManager) -> list[dict[str, Any]]:
    """Execute a SQL SELECT query on a specific database."""
    return db_manager.execute(db_id, sql)
