"""DuckDB implementation of the DatabaseEngine protocol."""

import re
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from src.database.config import DATA_DIR, DB_REGISTRY


class DuckDBEngine:
    """DuckDB implementation of the DatabaseEngine protocol."""

    def __init__(self, data_dir: str | Path = DATA_DIR) -> None:
        """Initialize DuckDBEngine with a data directory."""
        self.data_dir = Path(data_dir)
        self._allowed_db_ids = {db['id'] for db in DB_REGISTRY}

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
        """Get a connection to the specified database."""
        self._validate_db_id(db_id)
        path = self._get_path(db_id)
        if read_only and not path.exists():
            msg = f"Database '{db_id}' not found at {path}"
            raise FileNotFoundError(msg)
        return duckdb.connect(str(path), read_only=read_only)

    def initialize_schema(self) -> None:
        """Initialize the database schema for LMS and SIS."""
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
        with self._get_connection(db_id, read_only=False) as conn:
            if table_name == 'students':
                # Use subquery on df to find sids to delete, avoiding direct string interpolation of data
                conn.execute('DELETE FROM students WHERE sid IN (SELECT sid FROM df)')

            # Using identifiers in f-strings is generally unsafe but since we validated table_name
            # and db_id is whitelisted, this is controlled.
            # DuckDB's 'BY NAME' is safe for columns.
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
        with self._get_connection('sis_db', read_only=False) as conn:
            # table_name is validated
            conn.execute(
                f'CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM df LIMIT 0',
            )
            conn.execute(f'INSERT INTO {table_name} SELECT * FROM df')

    def list_tables(self, db_id: str) -> list[str]:
        """List all tables in the specified database."""
        # db_id validated in _get_connection
        with self._get_connection(db_id, read_only=True) as conn:
            tables = conn.execute('SHOW TABLES').fetchdf()
            return tables['name'].tolist()

    def get_table_schema(self, db_id: str, table_name: str) -> str:
        """Get the schema and sample data for a specific table."""
        self._validate_table_name(table_name)
        # db_id validated in _get_connection

        with self._get_connection(db_id, read_only=True) as conn:
            # Identifiers cannot be parameterized in standard SQL,
            # but we have validated table_name.
            cols = conn.execute(f'DESCRIBE {table_name}').fetchdf()
            sample = conn.execute(f'SELECT * FROM {table_name} LIMIT 3').fetchdf()

            col_lines = []
            for _, col in cols.iterrows():
                nullable = 'NULLABLE' if col['null'] == 'YES' else 'NOT NULL'
                col_lines.append(
                    f'    - {col["column_name"]} ({col["column_type"]}, {nullable})',
                )

            return (
                f'#### TABLE: {table_name}\n'
                f'- Columns:\n'
                + '\n'.join(col_lines)
                + f'\n- Sample data:\n```\n{sample.to_string(index=False)}\n```'
            )

    def execute(
        self,
        db_id: str,
        sql: str,
        read_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Execute a SQL query and return results as list of dicts."""
        # db_id validated in _get_connection

        sql_upper = sql.strip().upper()
        blocked = [
            'DROP',
            'DELETE',
            'INSERT',
            'UPDATE',
            'ALTER',
            'CREATE',
            'TRUNCATE',
            'COPY',
        ]
        if read_only:
            for keyword in blocked:
                if sql_upper.startswith(keyword):
                    return [
                        {
                            'error': f'Blocked: {keyword} statements are not allowed via this tool.',
                        },
                    ]

        try:
            with self._get_connection(db_id, read_only=read_only) as conn:
                result = conn.execute(sql).fetchdf()
                return result.to_dict(orient='records')
        except Exception as e:
            return [{'error': str(e)}]

    def update_intervention_status(self, sid: str, status: str) -> None:
        """Update the intervention lifecycle status for a specific student."""
        # Uses parameter binding which is safe
        with self._get_connection('sis_db', read_only=False) as conn:
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
