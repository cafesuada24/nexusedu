"""DuckDB implementation of the DatabaseEngine protocol."""

import contextlib
import re
import threading
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import sqlglot
from sqlglot import exp

from src.database.config import DATA_DIR, DB_REGISTRY


class DuckDBEngine:
    """DuckDB implementation of the DatabaseEngine protocol."""

    def __init__(self, data_dir: str | Path = DATA_DIR) -> None:
        """Initialize DuckDBEngine with a data directory."""
        self.data_dir = Path(data_dir)
        self._allowed_db_ids = {db['id'] for db in DB_REGISTRY}
        self._connections: dict[str, duckdb.DuckDBPyConnection] = {}
        self._write_lock = threading.RLock()

    def close(self) -> None:
        """Close all persistent connections."""
        for conn in self._connections.values():
            with contextlib.suppress(Exception):
                conn.close()
        self._connections.clear()

    def _validate_db_id(self, db_id: str) -> None:
        """Validate db_id against the registry."""
        if db_id not in self._allowed_db_ids:
            msg = f"Invalid or unauthorized database ID: '{db_id}'"
            raise ValueError(msg)

    def _validate_table_name(self, table_name: str) -> None:
        """Validate table name for alphanumeric/underscores only."""
        if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
            msg = f"Invalid table name: '{table_name}'. Only alphanumeric and underscores allowed."
            raise ValueError(msg)

    def _get_path(self, db_id: str) -> Path:
        """Resolve db_id to file path."""
        return self.data_dir / f'{db_id}.duckdb'

    def _get_connection(
        self,
        db_id: str,
        read_only: bool = True,
    ) -> duckdb.DuckDBPyConnection:
        """Get a connection to the specified database. Caches read-only connections."""
        self._validate_db_id(db_id)
        path = self._get_path(db_id)

        with self._write_lock:
            if read_only:
                if db_id not in self._connections:
                    if not path.exists():
                        msg = f"Database '{db_id}' not found at {path}"
                        raise FileNotFoundError(msg)
                    # Maintain a persistent, long-lived read_only=True DuckDB connection
                    self._connections[db_id] = duckdb.connect(str(path), read_only=True)
                return self._connections[db_id]

            # For write operations, we must close the cached read-only connection if it exists
            # because DuckDB doesn't allow mixed configurations in the same process for the same file.
            if db_id in self._connections:
                with contextlib.suppress(Exception):
                    self._connections[db_id].close()
                del self._connections[db_id]

            # For write operations, return a new connection
            return duckdb.connect(str(path), read_only=False)

    def initialize_schema(self) -> None:
        """Initialize the database schema for LMS and SIS."""
        with self._write_lock:
            # LMS schema
            with self._get_connection('lms_db', read_only=False) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS activities (
                        activity_id VARCHAR PRIMARY KEY,
                        sid VARCHAR,
                        course_id VARCHAR,
                        course_name VARCHAR,
                        test_type VARCHAR,
                        score DOUBLE,
                        timestamp DOUBLE,
                        academic_year INTEGER,
                        semester INTEGER
                    );
                """)

            # SIS schema
            with self._get_connection('sis_db', read_only=False) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS students (
                        sid VARCHAR PRIMARY KEY,
                        student_name VARCHAR,
                        email VARCHAR,
                        major VARCHAR DEFAULT 'Unknown',
                        current_risk_status VARCHAR DEFAULT 'Normal',
                        intervention_status VARCHAR DEFAULT 'none',
                        last_notified_timestamp DOUBLE DEFAULT 0,
                        last_notified_satisfaction INTEGER DEFAULT 0
                    );

                    CREATE TABLE IF NOT EXISTS student_status_history (
                        history_id VARCHAR PRIMARY KEY,
                        sid VARCHAR,
                        academic_year INTEGER,
                        semester INTEGER,
                        baseline_avg DOUBLE,
                        baseline_std DOUBLE,
                        current_score_avg DOUBLE,
                        z_score DOUBLE,
                        anomaly_flag VARCHAR,
                        status_recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)

    def ingest_records(
        self,
        db_id: str,
        table_name: str,
        records: Sequence[Mapping[str, Any]],
    ) -> None:
        """Ingest a list of dictionaries into a specified table."""
        if not records:
            return

        self._validate_table_name(table_name)
        # db_id is validated in _get_connection

        records_list = [dict(r) for r in records]
        if table_name == 'activities':
            for r in records_list:
                if 'activity_id' not in r:
                    r['activity_id'] = str(uuid.uuid4())

        df = pd.DataFrame(records_list)
        with self._write_lock, self._get_connection(db_id, read_only=False) as conn:
            if table_name == 'students':
                # Use validated table_name
                conn.execute(
                    f'DELETE FROM {table_name} WHERE sid IN (SELECT sid FROM df)',
                )

            # Use validated table_name
            conn.execute(f'INSERT INTO {table_name} BY NAME SELECT * FROM df')

    def ingest_custom_data(
        self,
        table_name: str,
        records: Sequence[Mapping[str, Any]],
    ) -> None:
        """Dynamically create and ingest custom data into SIS database."""
        if not records:
            return

        self._validate_table_name(table_name)

        df = pd.DataFrame(list(records))
        with self._write_lock, self._get_connection('sis_db', read_only=False) as conn:
                # Use validated table_name
                conn.execute(
                    f'CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM df LIMIT 0',
                )
                conn.execute(f'INSERT INTO {table_name} SELECT * FROM df')

    def list_tables(self, db_id: str) -> list[str]:
        """List all tables in the specified database."""
        # db_id validated in _get_connection
        conn = self._get_connection(db_id, read_only=True)
        res = conn.execute('SHOW TABLES').fetchall()
        return [row[0] for row in res]

    def get_table_schema(self, db_id: str, table_name: str) -> str:
        """Get the schema and sample data for a specific table."""
        self._validate_table_name(table_name)
        # db_id validated in _get_connection

        conn = self._get_connection(db_id, read_only=True)
        # Safely describe and sample using validated table_name
        rel_cols = conn.sql(f'DESCRIBE {table_name}')
        cols = [dict(zip(rel_cols.columns, r, strict=True)) for r in rel_cols.fetchall()]

        rel_sample = conn.sql(f'SELECT * FROM {table_name} LIMIT 3')
        sample_names = rel_sample.columns
        sample_rows = rel_sample.fetchall()

        col_lines: list[str] = []
        for col in cols:
            nullable = 'NULLABLE' if col['null'] == 'YES' else 'NOT NULL'
            col_lines.append(
                f'    - {col["column_name"]} ({col["column_type"]}, {nullable})',
            )

        # Build sample data string manually to avoid Pandas if possible,
        # but for small samples it's probably okay to use Pandas just for formatting
        # however, let's stick to simple formatting to be safe
        sample_str = ' | '.join(sample_names) + '\n' + '-' * 20 + '\n'
        for row in sample_rows:
            sample_str += ' | '.join(map(str, row)) + '\n'

        return (
            f'#### TABLE: {table_name}\n'
            f'- Columns:\n'
            + '\n'.join(col_lines)
            + f'\n- Sample data:\n```\n{sample_str}```'
        )

    def execute(
        self,
        db_id: str,
        sql: str,
        read_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Execute a SQL query and return results as list of dicts. Avoids Pandas for memory efficiency."""
        # db_id validated in _get_connection

        if read_only:
            try:
                # Use sqlglot to parse and validate the SQL
                expressions = sqlglot.parse(sql, read='duckdb')
                
                if len(expressions) != 1:
                    return [
                        {
                            'error': 'Blocked: Multiple statements are not allowed.',
                        },
                    ]
                
                expression = expressions[0]
                # Allowed statement types for read-only execution
                # WITH statements are parsed as exp.Select
                allowed_types = (exp.Select, exp.Describe, exp.Show)
                
                is_allowed = isinstance(expression, allowed_types)
                
                # Handle EXPLAIN which sqlglot may parse as a Command
                if not is_allowed and isinstance(expression, exp.Command):
                    if expression.this.upper() == 'EXPLAIN':
                        is_allowed = True
                
                if not is_allowed:
                    return [
                        {
                            'error': f'Blocked: Statement type {type(expression).__name__} is not allowed in read-only mode.',
                        },
                    ]
            except sqlglot.errors.ParseError as e:
                return [
                    {
                        'error': f'SQL Parse Error: {e}',
                    },
                ]

        try:
            conn = self._get_connection(db_id, read_only=read_only)
            if read_only:
                rel = conn.sql(sql)
                if rel is None:
                    return []
                names = rel.columns
                return [dict(zip(names, row, strict=True)) for row in rel.fetchall()]
            with self._write_lock, conn:
                    rel = conn.sql(sql)
                    if rel is None:
                        return []
                    names = rel.columns
                    return [dict(zip(names, row, strict=True)) for row in rel.fetchall()]
        except Exception as e:
            return [{'error': str(e)}]

    def update_intervention_status(self, sid: str, status: str) -> None:
        """Update the intervention lifecycle status for a specific student."""
        # Uses parameter binding which is safe
        with self._write_lock, self._get_connection('sis_db', read_only=False) as conn:
                conn.execute(
                    'UPDATE students SET intervention_status = ? WHERE sid = ?',
                    (status, sid),
                )

    def check_health(self) -> dict[str, str]:
        """Verify connectivity to LMS and SIS databases."""
        health_status: dict[str, str] = {}
        for db_id in ['lms_db', 'sis_db']:
            try:
                # db_id is whitelisted above
                with self._get_connection(db_id, read_only=True) as conn:
                    conn.execute('SELECT 1')
                    health_status[db_id] = 'healthy'
            except Exception as e:
                health_status[db_id] = f'unhealthy: {e}'
        return health_status
