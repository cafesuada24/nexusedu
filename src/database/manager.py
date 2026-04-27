"""Orchestrates database operations using injected engines and algorithms."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.database.config import DB_REGISTRY

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from src.database.interfaces import AnomalyAlgorithm, DatabaseEngine

class DatabaseManager[T_Engine: "DatabaseEngine", T_Algo: "AnomalyAlgorithm"]:
    """Orchestrates database operations using injected engine and anomaly algorithms."""

    def __init__(self) -> None:
        """Initialize DatabaseManager. Engine and algorithm can be injected later."""
        self._engine: T_Engine | None = None
        self._anomaly_algo: T_Algo | None = None

    def initialize(self, engine: T_Engine, anomaly_algo: T_Algo) -> None:
        """Inject dependencies and initialize the manager."""
        self._engine = engine
        self._anomaly_algo = anomaly_algo

    def _ensure_initialized(self) -> None:
        """Auto-initialize with defaults if not already done."""
        if self._engine is None:
            # Late import to avoid circular dependencies
            raise RuntimeError('DatabaseManager is not intitialized, please call `intialize`')

    def close(self) -> None:
        """Close any open resources."""
        if self._engine is not None:
            self._engine.close()
        self._engine = None
        self._anomaly_algo = None

    @property
    def engine(self) -> T_Engine:
        """Get the injected engine, auto-initializing if needed."""
        self._ensure_initialized()
        assert self._engine is not None
        return self._engine

    @property
    def anomaly_algo(self) -> T_Algo:
        """Get the injected algorithm, auto-initializing if needed."""
        self._ensure_initialized()
        assert self._anomaly_algo is not None
        return self._anomaly_algo


    def initialize_schema(self) -> None:
        """Initialize the database schema."""
        self.engine.initialize_schema()

    def ingest_records(
        self,
        db_id: str,
        table_name: str,
        records: Sequence[Mapping[str, str]],
    ) -> None:
        """Ingest records into a specified table."""
        self.engine.ingest_records(db_id, table_name, records)

    def ingest_custom_data(
        self,
        table_name: str,
        records: Sequence[Mapping[str, Any]],
    ) -> None:
        """Ingest custom data."""
        self.engine.ingest_custom_data(table_name, records)

    def run_anomaly_engine(self) -> None:
        """Run the configured anomaly detection algorithm."""
        self.anomaly_algo.run(self.engine)

    def update_intervention_status(self, sid: str, status: str) -> None:
        """Update the intervention lifecycle status for a specific student."""
        self.engine.update_intervention_status(sid, status)

    def check_health(self) -> dict[str, Any]:
        """Verify database health."""
        return self.engine.check_health()

    def list_tables(self, db_id: str) -> list[str]:
        """List all tables in the specified database."""
        return self.engine.list_tables(db_id)

    def get_table_schema(self, db_id: str, table_name: str) -> str:
        """Get the schema and sample data for a specific table."""
        return self.engine.get_table_schema(db_id, table_name)

    def execute(
        self,
        db_id: str,
        sql: str,
        read_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Execute a SQL query and return results."""
        return self.engine.execute(db_id, sql, read_only=read_only)

    def get_formatted_db_list(self) -> str:
        """Retrieve list of available databases in markdown format."""
        header = '## AVAILABLE DATABASE REGISTRY\n'
        entries = []
        for db in DB_REGISTRY:
            entry = f'### ID: `{db["id"]}`\n- **Description**: {db["description"]}\n- **Keywords**: {", ".join(db["keywords"])}\n'
            entries.append(entry)
        return header + '\n---\n'.join(entries)

    def get_formatted_table_list(self, db_id: str) -> str:
        """List all tables available in the specified database in markdown format."""
        try:
            tables = self.list_tables(db_id)
            return f'## Tables in {db_id}:' + '\n- '.join(tables)
        except Exception as e:
            return f'Error: {e}'

    def get_formatted_table_schema(self, db_id: str, table_name: str) -> str:
        """Get the detailed schema and sample data for a specific table in markdown format."""
        try:
            return self.get_table_schema(db_id, table_name)
        except Exception as e:
            return f'Error: {e}'

    def get_formatted_db_schema(self, db_id: str) -> str:
        """Get the detailed schema of a specific database in markdown format."""
        try:
            tables = self.list_tables(db_id)
            schemas = [self.get_table_schema(db_id, t) for t in tables]
            return f'### DATABASE: {db_id.upper()}\n' + '\n\n'.join(schemas)
        except Exception as e:
            return f'Error: {e}'
