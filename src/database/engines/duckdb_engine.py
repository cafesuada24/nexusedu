"""DuckDB implementation of the DatabaseEngine protocol."""

import contextlib
import os
import re
import threading
import uuid
from collections.abc import Generator, Iterator, Mapping, Sequence
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

        # Check for MotherDuck token
        md_token = os.getenv('MOTHERDUCK_TOKEN')
        self.is_motherduck = bool(md_token)

        if self.is_motherduck:
            try:
                # Connect to MotherDuck
                self._main_conn = duckdb.connect(f'md:?motherduck_token={md_token}')
            except Exception:
                self.is_motherduck = False
                pass

        if not self.is_motherduck:
            # Use a single main connection and ATTACH other databases to it.
            # This allows cross-database joins and avoids "file already open" errors.
            self._main_conn = duckdb.connect()
            # Performance optimizations for concurrency

        # Shared performance settings
        self._main_conn.execute('PRAGMA enable_checkpoint_on_shutdown')
        self._main_conn.execute("PRAGMA checkpoint_threshold='1GB'")
        self._main_conn.execute('PRAGMA threads=8')

        # Strict Sandboxing for Security
        self._main_conn.execute('SET allow_unsigned_extensions=false')
        # We don't use enable_external_access=false because we need to ATTACH local .duckdb files.
        # But we can disable extension loading/installing to prevent malicious extensions.
        self._main_conn.execute('SET autoinstall_known_extensions=false')
        self._main_conn.execute('SET autoload_known_extensions=false')

        self._attached_dbs: set[str] = set()
        self.write_lock = threading.RLock()

    def close(self) -> None:
        """Close all persistent connections."""
        with contextlib.suppress(Exception):
            self._main_conn.close()
        self._attached_dbs.clear()

    def _validate_db_id(self, db_id: str) -> None:
        """Validate db_id against the registry and for alphanumeric format."""
        if not re.match(r'^[a-zA-Z0-9_]+$', db_id):
            msg = f"Invalid database ID format: '{db_id}'. Only alphanumeric and underscores allowed."
            raise ValueError(msg)
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

    @contextlib.contextmanager

    def get_cursor(self, db_id: str) -> Generator[duckdb.DuckDBPyConnection]:
        """Get a cursor to the specified database. Ensures the cursor is closed after use."""
        self._validate_db_id(db_id)

        with self.write_lock:
            if db_id not in self._attached_dbs:
                if self.is_motherduck:
                    # Resolve to MotherDuck database
                    self._main_conn.execute(f"ATTACH 'md:{db_id}' AS {db_id}")
                else:
                    path = self._get_path(db_id)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    # Attach the database file using its ID as alias
                    self._main_conn.execute(f"ATTACH '{path}' AS {db_id}")
                self._attached_dbs.add(db_id)

        # Return a cursor that defaults to the requested database
        cursor = self._main_conn.cursor()
        try:
            cursor.execute(f'USE {db_id}')
            yield cursor
        finally:
            cursor.close()

    def initialize_schema(self) -> None:
        """Initialize the database schema for LMS and SIS."""
        with self.write_lock:
            # LMS schema
            with self.get_cursor('lms_db') as cursor:
                cursor.execute("""
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
            with self.get_cursor('sis_db') as cursor:
                cursor.execute("""
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

                    CREATE TABLE IF NOT EXISTS advisors (
                        advisor_id VARCHAR PRIMARY KEY,
                        name VARCHAR,
                        email VARCHAR
                    );

                    CREATE TABLE IF NOT EXISTS advisor_points_ledger (
                        id VARCHAR PRIMARY KEY,
                        advisor_id VARCHAR,
                        action_type VARCHAR,
                        points INTEGER,
                        sid VARCHAR,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        # db_id is validated in _get_cursor

        records_list = [dict(r) for r in records]
        if table_name == 'activities':
            for r in records_list:
                if 'activity_id' not in r:
                    r['activity_id'] = str(uuid.uuid4())

        df = pd.DataFrame(records_list)
        with self.write_lock, self.get_cursor(db_id) as cursor:
            cursor.begin()
            try:
                if table_name == 'students':
                    # Use validated table_name
                    cursor.execute(
                        f'DELETE FROM {table_name} WHERE sid IN (SELECT sid FROM df)',
                    )

                # Use validated table_name
                cursor.execute(f'INSERT INTO {table_name} BY NAME SELECT * FROM df')
                cursor.commit()
            except Exception:
                cursor.rollback()
                raise

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
        with self.write_lock, self.get_cursor('sis_db') as cursor:
            cursor.begin()
            try:
                # Use validated table_name
                cursor.execute(
                    f'CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM df LIMIT 0',
                )
                cursor.execute(f'INSERT INTO {table_name} SELECT * FROM df')
                cursor.commit()
            except Exception:
                cursor.rollback()
                raise

    def list_tables(self, db_id: str) -> list[str]:
        """List all tables in the specified database."""
        # db_id validated in _get_cursor
        with self.get_cursor(db_id) as cursor:
            res = cursor.execute('SHOW TABLES').fetchall()
            return [row[0] for row in res]

    def get_table_schema(self, db_id: str, table_name: str) -> str:
        """Get the schema and sample data for a specific table."""
        self._validate_table_name(table_name)
        # db_id validated in _get_cursor

        with self.get_cursor(db_id) as cursor:
            # Safely describe and sample using validated table_name
            rel_cols = cursor.sql(f'DESCRIBE {table_name}')
            cols = [
                dict(zip(rel_cols.columns, r, strict=True)) for r in rel_cols.fetchall()
            ]

            rel_sample = cursor.sql(f'SELECT * FROM {table_name} LIMIT 3')
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

    def _validate_read_only_sql(self, sql: str) -> str | None:
        """Validate that the SQL is read-only. Returns an error message if invalid."""
        try:
            # Use sqlglot to parse and validate the SQL
            expressions = sqlglot.parse(sql, read='duckdb')

            if len(expressions) != 1:
                return 'Blocked: Multiple statements are not allowed.'

            expression = expressions[0]
            # Allowed statement types for read-only execution
            # WITH statements are parsed as exp.Select
            allowed_types = (exp.Select, exp.Describe, exp.Show)

            is_allowed = isinstance(expression, allowed_types)

            # Handle EXPLAIN which sqlglot may parse as a Command
            if (
                not is_allowed
                and isinstance(expression, exp.Command)
                and expression.this.upper() == 'EXPLAIN'
            ):
                is_allowed = True

            if not is_allowed:
                return f'Blocked: Statement type {type(expression).__name__} is not allowed in read-only mode.'

        except sqlglot.ParseError as e:
            return f'SQL Parse Error: {e}'

        return None

    def execute(
        self,
        db_id: str,
        sql: str,
        params: Sequence[str | int] | Mapping[str, int | str] | None = None,
        read_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Execute a SQL query and return results as list of dicts. Avoids Pandas for memory efficiency."""
        # db_id validated in _get_cursor

        if read_only:
            error = self._validate_read_only_sql(sql)
            if error:
                return [{'error': error}]

        try:
            if read_only:
                with self.get_cursor(db_id) as cursor:
                    cursor.execute(sql, params)
                    names = [desc[0] for desc in cursor.description]
                    return [
                        dict(zip(names, row, strict=True)) for row in cursor.fetchall()
                    ]

            with self.write_lock, self.get_cursor(db_id) as cursor:
                cursor.execute(sql, params)
                names = [desc[0] for desc in cursor.description]
                return [
                    dict(zip(names, row, strict=True)) for row in cursor.fetchall()
                ]
        except Exception as e:
            return [{'error': str(e)}]

    def update_intervention_status(self, sid: str, status: str) -> None:
        """Update the intervention lifecycle status for a specific student."""
        # Uses parameter binding which is safe
        with self.write_lock, self.get_cursor('sis_db') as cursor:
            cursor.execute(
                'UPDATE students SET intervention_status = ? WHERE sid = ?',
                (status, sid),
            )

    def inject_points(self, advisor_id: str, sid: str, action_type: str) -> None:
        """Inject points for an advisor action with response time multiplier."""
        matrix = {
            'draft_reviewed': 5,
            'email_sent': 10,
            'meeting_booked': 50,
            'student_resolved': 100,
        }
        base_points = matrix.get(action_type, 0)
        if base_points == 0:
            return

        with self.write_lock, self.get_cursor('sis_db') as cursor:
            # Check for response time bonus (24h SLA)
            # Find the most recent status record for this student
            res = cursor.execute(
                'SELECT status_recorded_at FROM student_status_history WHERE sid = ? ORDER BY status_recorded_at DESC LIMIT 1',
                (sid,),
            ).fetchone()

            multiplier = 1.0
            if res:
                recorded_at = res[0]
                # Compare current_timestamp with recorded_at using DuckDB SQL
                is_within_24h = cursor.execute(
                    'SELECT (epoch(current_timestamp) - epoch(?)) < 86400',
                    (recorded_at,),
                ).fetchone()
                if is_within_24h and is_within_24h[0]:
                    multiplier = 1.2

            final_points = int(base_points * multiplier)
            ledger_id = str(uuid.uuid4())

            cursor.execute(
                'INSERT INTO advisor_points_ledger (id, advisor_id, action_type, points, sid) VALUES (?, ?, ?, ?, ?)',
                (ledger_id, advisor_id, action_type, final_points, sid),
            )

    def check_health(self) -> dict[str, str]:
        """Verify connectivity to LMS and SIS databases."""
        health_status: dict[str, str] = {}
        for db_id in ['lms_db', 'sis_db']:
            try:
                # db_id is whitelisted above
                with self.get_cursor(db_id) as cursor:
                    cursor.execute('SELECT 1')
                health_status[db_id] = 'healthy'
            except Exception as e:
                health_status[db_id] = f'unhealthy: {e}'
        return health_status
