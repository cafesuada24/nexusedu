"""Orchestrates database operations using injected engines and algorithms."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from src.database.interfaces import AnomalyAlgorithm, DatabaseEngine

class DatabaseManager:
    """Orchestrates database operations using injected engine and anomaly algorithms."""

    def __init__(self) -> None:
        """Initialize DatabaseManager. Engine and algorithm can be injected later."""
        self._engine: DatabaseEngine | None = None
        self._anomaly_algo: AnomalyAlgorithm | None = None

    def initialize(self, engine: DatabaseEngine, anomaly_algo: AnomalyAlgorithm) -> None:
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
    def engine(self) -> DatabaseEngine:
        """Get the injected engine, auto-initializing if needed."""
        self._ensure_initialized()
        assert self._engine is not None
        return self._engine

    @property
    def anomaly_algo(self) -> AnomalyAlgorithm:
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
