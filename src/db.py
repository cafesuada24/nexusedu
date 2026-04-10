"""Database Manager & LangChain Tools for multi-source DB access.

Provides a universal interface for the LLM Agent to discover,
inspect, and query multiple database sources (LMS, SIS) via DuckDB.
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
from langchain_core.tools import tool

# Thư mục chứa các file .duckdb — resolve từ gốc project
DATA_DIR = Path(__file__).resolve().parent.parent / 'data'

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

    def get_schema(self, db_id: str) -> str:
        """Read live schema from DuckDB file.

        Returns a semantically enriched schema summary
        designed for high-accuracy SQL generation.
        """
        path = self._get_path(db_id)
        conn = duckdb.connect(str(path), read_only=True)

        try:
            tables = conn.execute('SHOW TABLES').fetchdf()
            schema_parts = [
                f'### DATABASE: {db_id.upper()}\n'
                f'Dialect: DuckDB (SQL standard)\n'
            ]

            for table_name in tables['name']:
                cols = conn.execute(f'DESCRIBE {table_name}').fetchdf()

                # Sample 3 rows
                sample = conn.execute(
                    f'SELECT * FROM {table_name} LIMIT 3'
                ).fetchdf()

                col_lines = []
                for _, col in cols.iterrows():
                    nullable = 'NULLABLE' if col['null'] == 'YES' else 'NOT NULL'
                    col_lines.append(
                        f'    - {col["column_name"]} ({col["column_type"]}, {nullable})'
                    )

                schema_parts.append(
                    f'\n#### TABLE: {table_name}\n'
                    f'- Columns:\n' + '\n'.join(col_lines) +
                    f'\n- Sample data:\n```\n{sample.to_string(index=False)}\n```'
                )

            return '\n'.join(schema_parts)

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
def get_db_schema(db_id: str) -> str:
    """Get the detailed schema of a specific database.

    Returns table names, column names/types, and sample data
    to help write accurate SQL queries.

    Args:
        db_id: The database ID from get_db_list (e.g., 'lms_db' or 'sis_db').
    """
    try:
        return db_manager.get_schema(db_id)
    except FileNotFoundError as e:
        return f'Error: {e}'


@tool
def execute_sql(db_id: str, sql: str) -> str:
    """Execute a SQL query on a specific database and return results.

    Must call get_db_schema first to understand the table structure.
    Only SELECT queries are allowed. Use LIMIT to control output size.

    Args:
        db_id: The database ID (e.g., 'lms_db' or 'sis_db').
        sql: A valid SQL SELECT query.
    """
    results = db_manager.execute(db_id, sql)

    if not results:
        return 'Query returned no results.'

    if len(results) == 1 and 'error' in results[0]:
        return results[0]['error']

    # Format as markdown table for LLM readability
    import pandas as pd
    df = pd.DataFrame(results)
    return df.to_markdown(index=False)
