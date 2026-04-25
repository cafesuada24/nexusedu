"""Database Manager & LangChain Tools for multi-source DB access.

Provides a universal interface for the LLM Agent to discover,
inspect, and query multiple database sources (LMS, SIS) via DuckDB.
"""

from __future__ import annotations

import uuid
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
            'Source for student academic performance and assessment activities.'
        ),
        'dialect': 'duckdb',
        'keywords': [
            'assessment score',
            'student performance',
            'activities',
            'quizzes',
            'academic year',
            'semester',
            'sid',
        ],
    },
    {
        'id': 'sis_db',
        'description': (
            'Student Information System (SIS). '
            'Source for administrative profiles and longitudinal risk history.'
        ),
        'dialect': 'duckdb',
        'keywords': [
            'student profile',
            'students',
            'risk status',
            'intervention status',
            'kanban state',
            'anomaly history',
            'nudge history',
            'sid',
        ],
    },
]


# ============================================================================
# DATABASE MANAGER
# ============================================================================


class DatabaseManager:
    """Manages connections to multiple DuckDB sources.

    Resolves db_id to file path using convention: data/{db_id}.duckdb
    """

    def __init__(self, data_dir: str | Path = DATA_DIR) -> None:
        self.data_dir = Path(data_dir)

    def _get_path(self, db_id: str) -> Path:
        """Resolve db_id to file path."""
        path = self.data_dir / f'{db_id}.duckdb'
        return path

    def _get_connection(
        self, db_id: str, read_only: bool = True
    ) -> duckdb.DuckDBPyConnection:
        """Get a connection to the specified database."""
        path = self._get_path(db_id)
        if read_only and not path.exists():
            msg = f"Database '{db_id}' not found at {path}"
            raise FileNotFoundError(msg)
        return duckdb.connect(str(path), read_only=read_only)

    def initialize_schema(self) -> None:
        """Initialize the database schema for LMS and SIS."""
        # LMS Schema: activities
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

        # SIS Schema: students and status history
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
        records: list[dict[str, object]],
    ) -> None:
        """Ingest a list of dictionaries into a specified table."""
        if not records:
            return

        # Add primary keys if missing for activities
        if table_name == 'activities':
            for r in records:
                if 'activity_id' not in r:
                    r['activity_id'] = str(uuid.uuid4())

        df = pd.DataFrame(records)
        with self._get_connection(db_id, read_only=False) as conn:
            # Upsert logic: Delete existing records if we have a PK match to allow updates
            if table_name == 'students':
                conn.execute(
                    f'DELETE FROM {table_name} WHERE sid IN (SELECT sid FROM df)',
                )

            conn.execute(f'INSERT INTO {table_name} BY NAME SELECT * FROM df')

    def ingest_custom_data(
        self,
        table_name: str,
        records: list[dict[str, object]],
    ) -> None:
        """Dynamically create and ingest custom data into SIS database."""
        if not records:
            return
        df = pd.DataFrame(records)
        with self._get_connection('sis_db', read_only=False) as conn:
            conn.execute(
                f'CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM df LIMIT 0',
            )
            conn.execute(f'INSERT INTO {table_name} SELECT * FROM df')

    def run_anomaly_engine(self) -> None:
        """Calculate baselines and anomalies, updating the history table."""
        with self._get_connection('sis_db', read_only=False) as conn:
            lms_path = self._get_path('lms_db')
            conn.execute(f"ATTACH '{lms_path}' AS lms")

            # 1. Calculate and insert new history records
            conn.execute("""
                INSERT INTO student_status_history (
                    history_id, sid, academic_year, semester, 
                    baseline_avg, baseline_std, current_score_avg, z_score, anomaly_flag
                )
                WITH semester_stats AS (
                    SELECT
                        sid,
                        academic_year,
                        semester,
                        AVG(score) as avg_score
                    FROM lms.activities
                    GROUP BY sid, academic_year, semester
                ),
                historical_stats AS (
                    SELECT
                        sid,
                        academic_year,
                        semester,
                        avg_score,
                        AVG(avg_score) OVER (
                            PARTITION BY sid
                            ORDER BY academic_year, semester
                            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                        ) as baseline_avg,
                        STDDEV(avg_score) OVER (
                            PARTITION BY sid
                            ORDER BY academic_year, semester
                            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                        ) as baseline_std
                    FROM semester_stats
                )
                SELECT
                    uuid() as history_id,
                    sid,
                    academic_year,
                    semester,
                    baseline_avg,
                    baseline_std,
                    avg_score as current_score_avg,
                    (avg_score - baseline_avg) / NULLIF(baseline_std, 0) as z_score,
                    CASE
                        WHEN (avg_score - baseline_avg) / NULLIF(baseline_std, 0) < -1.5 THEN 'Significant Drop'
                        WHEN avg_score < baseline_avg * 0.7 THEN 'Critical Drop'
                        ELSE 'Normal'
                    END as anomaly_flag
                FROM historical_stats
                WHERE baseline_avg IS NOT NULL
                AND (sid, academic_year, semester) NOT IN (SELECT sid, academic_year, semester FROM student_status_history);
            """)

            # 2. Update current risk and intervention status in students table
            conn.execute("""
                UPDATE students
                SET
                    current_risk_status = h.anomaly_flag,
                    intervention_status = CASE
                        WHEN h.anomaly_flag != 'Normal' AND intervention_status IN ('none', 'resolved', 'expired')
                        THEN 'new'
                        ELSE intervention_status
                    END
                FROM (
                    SELECT sid, anomaly_flag
                    FROM student_status_history
                    QUALIFY ROW_NUMBER() OVER (PARTITION BY sid ORDER BY academic_year DESC, semester DESC) = 1
                ) h
                WHERE students.sid = h.sid;
            """)

            conn.execute('DETACH lms')

    def update_intervention_status(self, sid: str, status: str) -> None:
        """Update the intervention lifecycle status for a specific student."""
        with self._get_connection('sis_db', read_only=False) as conn:
            conn.execute(
                'UPDATE students SET intervention_status = ? WHERE sid = ?',
                (status, sid),
            )

    def list_tables(self, db_id: str) -> list[str]:
        """List all tables in the specified database."""
        with self._get_connection(db_id, read_only=True) as conn:
            tables = conn.execute('SHOW TABLES').fetchdf()
            return tables['name'].tolist()

    def get_table_schema(self, db_id: str, table_name: str) -> str:
        """Get the schema and sample data for a specific table."""
        with self._get_connection(db_id, read_only=True) as conn:
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

    def execute(self, db_id: str, sql: str) -> list[dict[object, object]]:
        """Execute a read-only SQL query and return results as list of dicts."""
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
        for keyword in blocked:
            if sql_upper.startswith(keyword):
                return [
                    {
                        'error': f'Blocked: {keyword} statements are not allowed via this tool.'
                    },
                ]

        try:
            with self._get_connection(db_id, read_only=True) as conn:
                result = conn.execute(sql).fetchdf()
                if len(result) > 50:
                    return result.head(50).to_dict(orient='records') + [
                        {'_truncated': f'Showing 50 of {len(result)} rows.'},
                    ]
                return result.to_dict(orient='records')
        except Exception as e:
            return [{'error': str(e)}]


# Singleton instance
db_manager = DatabaseManager()


# ============================================================================
# LANGCHAIN TOOLS
# ============================================================================


@tool
def get_db_list() -> str:
    """Retrieve list of available databases."""
    header = '## AVAILABLE DATABASE REGISTRY\n'
    entries = []
    for db in DB_REGISTRY:
        entry = f'### ID: `{db["id"]}`\n- **Description**: {db["description"]}\n- **Keywords**: {", ".join(db["keywords"])}\n'
        entries.append(entry)
    return header + '\n---\n'.join(entries)


@tool
def list_tables(db_id: str) -> str:
    """List all tables available in the specified database."""
    try:
        tables = db_manager.list_tables(db_id)
        return f'## Tables in {db_id}:' + '\n- '.join(tables)
    except Exception as e:
        return f'Error: {e}'


@tool
def describe_table(db_id: str, table_name: str) -> str:
    """Get the detailed schema and sample data for a specific table."""
    try:
        return db_manager.get_table_schema(db_id, table_name)
    except Exception as e:
        return f'Error: {e}'


def get_db_schema(db_id: str) -> str:
    """Get the detailed schema of a specific database."""
    try:
        tables = db_manager.list_tables(db_id)
        schemas = [db_manager.get_table_schema(db_id, t) for t in tables]
        return f'### DATABASE: {db_id.upper()}\n' + '\n\n'.join(schemas)
    except Exception as e:
        return f'Error: {e}'


def execute_sql(db_id: str, sql: str) -> list[dict[object, object]]:
    """Execute a SQL SELECT query on a specific database."""
    return db_manager.execute(db_id, sql)
