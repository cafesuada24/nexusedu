"""Database Manager & LangChain Tools for multi-source DB access.

Provides a universal interface for the LLM Agent to discover,
inspect, and query multiple database sources (LMS, SIS) via DuckDB.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
from langchain_core.tools import tool

# Thư mục chứa các file .duckdb — resolve từ gốc project
DATA_DIR = 'data'

# ============================================================================
# DATABASE REGISTRY
# ============================================================================

DB_REGISTRY = [
    {
        'id': 'lms_db',
        'description': (
            'Learning Management System (LMS). '
            'Source for student academic performance, VLE engagement (click logs), '
            'risk scores, and course module results. Based on real OULAD dataset.'
        ),
        'dialect': 'duckdb',
        'keywords': [
            'risk score',
            'VLE clicks',
            'assessment score',
            'student performance',
            'final result',
            'pass fail withdrawn',
        ],
    },
    {
        'id': 'sis_db',
        'description': (
            'Student Information System (SIS). '
            'Source for administrative, financial, and demographic student data '
            'including billing, enrollment status, and personal profiles.'
        ),
        'dialect': 'duckdb',
        'keywords': [
            'tuition',
            'billing',
            'enrollment',
            'student profile',
            'scholarship',
            'part-time job',
        ],
    },
]


# ============================================================================
# DATABASE MANAGER
# ============================================================================

class DatabaseManager:
    """Manages read-only connections to multiple DuckDB sources.

    Resolves db_id to file path using convention: data/{db_id}.duckdb
    """

    def __init__(self, data_dir: str | Path = DATA_DIR) -> None:
        self.data_dir = Path(data_dir)

    def _get_path(self, db_id: str) -> Path:
        """Resolve db_id to file path."""
        path = self.data_dir / f'{db_id}.duckdb'
        if not path.exists():
            msg = f"Database '{db_id}' not found at {path}"
            raise FileNotFoundError(msg)
        return path

    def list_tables(self, db_id: str) -> list[str]:
        """List all tables in the specified database."""
        path = self._get_path(db_id)
        conn = duckdb.connect(str(path), read_only=True)
        try:
            tables = conn.execute('SHOW TABLES').fetchdf()
            return tables['name'].tolist()
        finally:
            conn.close()

    def get_table_schema(self, db_id: str, table_name: str) -> str:
        """Get the schema and sample data for a specific table."""
        path = self._get_path(db_id)
        conn = duckdb.connect(str(path), read_only=True)
        try:
            cols = conn.execute(f'DESCRIBE {table_name}').fetchdf()
            sample = conn.execute(f'SELECT * FROM {table_name} LIMIT 3').fetchdf()

            col_lines = []
            for _, col in cols.iterrows():
                nullable = 'NULLABLE' if col['null'] == 'YES' else 'NOT NULL'
                col_lines.append(
                    f'    - {col["column_name"]} ({col["column_type"]}, {nullable})'
                )

            return (
                f'#### TABLE: {table_name}\n'
                f'- Columns:\n' + '\n'.join(col_lines) +
                f'\n- Sample data:\n```\n{sample.to_string(index=False)}\n```'
            )
        finally:
            conn.close()

    def execute(self, db_id: str, sql: str) -> list[dict]:
        """Execute a read-only SQL query and return results as list of dicts.

        Args:
            db_id: Database identifier (e.g., 'lms_db', 'sis_db').
            sql: SQL query string. Only SELECT statements are allowed.

        Returns:
            List of dictionaries, one per row.
        """
        # Safety: block destructive statements
        sql_upper = sql.strip().upper()
        blocked = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'TRUNCATE']
        for keyword in blocked:
            if sql_upper.startswith(keyword):
                return [{'error': f'Blocked: {keyword} statements are not allowed.'}]

        path = self._get_path(db_id)
        conn = duckdb.connect(str(path), read_only=True)

        try:
            result = conn.execute(sql).fetchdf()
            # Limit output to avoid overwhelming the LLM context
            if len(result) > 50:
                return (
                    result.head(50).to_dict(orient='records')
                    + [{'_truncated': f'Showing 50 of {len(result)} rows. Use LIMIT or WHERE to narrow results.'}]
                )
            return result.to_dict(orient='records')

        except duckdb.Error as e:
            return [{'error': f'SQL Error on {db_id}: {e!s}'}]

        finally:
            conn.close()


# Singleton instance
db_manager = DatabaseManager()


# ============================================================================
# LANGCHAIN TOOLS
# ============================================================================

@tool
def get_db_list() -> str:
    """Retrieve list of available databases with descriptions and keywords.

    Use this tool first to understand what data sources are available
    before querying any specific database.
    """
    header = '## AVAILABLE DATABASE REGISTRY\n'
    entries = []

    for db in DB_REGISTRY:
        entry = (
            f'### ID: `{db["id"]}`\n'
            f'- **Description**: {db["description"]}\n'
            f'- **Dialect**: {db["dialect"]}\n'
            f'- **Keywords**: {", ".join(db["keywords"])}\n'
        )
        entries.append(entry)

    return header + '\n---\n'.join(entries)


@tool
def list_tables(db_id: str) -> str:
    """List all tables available in the specified database.

    Use this after get_db_list to narrow down which tables to inspect.

    Args:
        db_id: The database ID (e.g., 'lms_db', 'sis_db').
    """
    try:
        tables = db_manager.list_tables(db_id)
        return f"Tables in {db_id}: " + ", ".join(tables)
    except FileNotFoundError as e:
        return f"Error: {e}"


@tool
def describe_table(db_id: str, table_name: str) -> str:
    """Get the detailed schema and sample data for a specific table.

    Use this tool only after you have identified a specific table of interest
    using list_tables.

    Args:
        db_id: The database ID (e.g., 'lms_db', 'sis_db').
        table_name: The name of the table to describe.
    """
    try:
        return db_manager.get_table_schema(db_id, table_name)
    except Exception as e:
        return f"Error describing table {table_name}: {e}"


def get_db_schema(db_id: str) -> str:
    """Get the detailed schema of a specific database.

    Returns table names, column names/types, and sample data
    to help write accurate SQL queries.

    Args:
        db_id: The database ID from get_db_list (e.g., 'lms_db' or 'sis_db').
    """
    try:
        tables = db_manager.list_tables(db_id)
        schemas = [db_manager.get_table_schema(db_id, t) for t in tables]
        return f"### DATABASE: {db_id.upper()}\n" + "\n\n".join(schemas)
    except FileNotFoundError as e:
        return f"Error: {e}"


def execute_sql(db_id: str, sql: str) -> list[dict]:
    """Execute a SQL query on a specific database and return results.

    Must call list_tables/describe_table first to understand the table structure.
    Only SELECT queries are allowed. Use LIMIT to control output size.

    Args:
        db_id: The database ID (e.g., 'lms_db' or 'sis_db').
        sql: A valid SQL SELECT query.
    """
    return db_manager.execute(db_id, sql)
