"""Orchestrates database operations using injected engines and algorithms."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from src.database.config import DB_REGISTRY

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from src.database.interfaces import AnomalyAlgorithm, DatabaseEngine


class DatabaseManager:
    """Orchestrates database operations using injected engine and anomaly algorithms."""

    def __init__(self) -> None:
        """Initialize DatabaseManager. Engine and algorithm can be injected later."""
        self._engine: DatabaseEngine | None = None
        self._anomaly_algo: AnomalyAlgorithm | None = None

    def initialize(
        self,
        engine: DatabaseEngine,
        anomaly_algo: AnomalyAlgorithm,
    ) -> None:
        """Inject dependencies and initialize the manager."""
        self._engine = engine
        self._anomaly_algo = anomaly_algo

    def _ensure_initialized(self) -> None:
        """Auto-initialize with defaults if not already done."""
        if self._engine is None:
            # Late import to avoid circular dependencies
            raise RuntimeError(
                'DatabaseManager is not intitialized, please call `intialize`',
            )

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

    async def initialize_schema_async(self) -> None:
        """Initialize the database schema asynchronously."""
        await asyncio.to_thread(self.engine.initialize_schema)

    def ingest_records(
        self,
        db_id: str,
        table_name: str,
        records: Sequence[Mapping[str, Any]],
    ) -> None:
        """Ingest records into a specified table."""
        self.engine.ingest_records(db_id, table_name, records)

    async def ingest_records_async(
        self,
        db_id: str,
        table_name: str,
        records: Sequence[Mapping[str, Any]],
    ) -> None:
        """Ingest records into a specified table asynchronously."""
        await asyncio.to_thread(self.engine.ingest_records, db_id, table_name, records)

    def ingest_custom_data(
        self,
        table_name: str,
        records: Sequence[Mapping[str, Any]],
    ) -> None:
        """Ingest custom data."""
        self.engine.ingest_custom_data(table_name, records)

    async def ingest_custom_data_async(
        self,
        table_name: str,
        records: Sequence[Mapping[str, Any]],
    ) -> None:
        """Ingest custom data asynchronously."""
        await asyncio.to_thread(self.engine.ingest_custom_data, table_name, records)

    def run_anomaly_engine(self) -> list[str]:
        """Run the configured anomaly detection algorithm.

        Returns:
            List of student IDs (SIDs) whose status transitioned to 'new'.
        """
        return self.anomaly_algo.run(self.engine)

    async def run_anomaly_engine_async(self) -> list[str]:
        """Run the configured anomaly detection algorithm asynchronously."""
        return await asyncio.to_thread(self.anomaly_algo.run, self.engine)

    def update_intervention_status(self, sid: str, status: str) -> None:
        """Update the intervention lifecycle status for a specific student."""
        self.engine.update_intervention_status(sid, status)

    async def update_intervention_status_async(self, sid: str, status: str) -> None:
        """Update the intervention lifecycle status for a specific student asynchronously."""
        await asyncio.to_thread(self.engine.update_intervention_status, sid, status)

    def update_draft_job_ids(self, updates: list[tuple[str, str]]) -> None:
        """Batch update the draft_job_id for multiple students."""
        self.engine.update_draft_job_ids(updates)

    async def update_draft_job_ids_async(self, updates: list[tuple[str, str]]) -> None:
        """Batch update the draft_job_id for multiple students asynchronously."""
        await asyncio.to_thread(self.engine.update_draft_job_ids, updates)

    def inject_points(self, advisor_id: str, sid: str, action_type: str) -> None:
        """Inject points for an advisor action into the points ledger."""
        self.engine.inject_points(advisor_id, sid, action_type)

    async def inject_points_async(self, advisor_id: str, sid: str, action_type: str) -> None:
        """Inject points for an advisor action into the points ledger asynchronously."""
        await asyncio.to_thread(self.engine.inject_points, advisor_id, sid, action_type)

    def check_idempotency(self, key: str) -> bool:
        """Check if an idempotency key has already been used."""
        return self.engine.check_idempotency(key)

    async def check_idempotency_async(self, key: str) -> bool:
        """Check if an idempotency key has already been used asynchronously."""
        return await asyncio.to_thread(self.engine.check_idempotency, key)

    def record_idempotency(self, key: str) -> None:
        """Record an idempotency key."""
        self.engine.record_idempotency(key)

    async def record_idempotency_async(self, key: str) -> None:
        """Record an idempotency key asynchronously."""
        await asyncio.to_thread(self.engine.record_idempotency, key)

    def check_health(self) -> dict[str, Any]:
        """Verify database health."""
        return self.engine.check_health()

    async def check_health_async(self) -> dict[str, Any]:
        """Verify database health asynchronously."""
        return await asyncio.to_thread(self.engine.check_health)

    def list_tables(self, db_id: str) -> list[str]:
        """List all tables in the specified database."""
        return self.engine.list_tables(db_id)

    async def list_tables_async(self, db_id: str) -> list[str]:
        """List all tables in the specified database asynchronously."""
        return await asyncio.to_thread(self.engine.list_tables, db_id)

    def get_table_schema(self, db_id: str, table_name: str) -> str:
        """Get the schema and sample data for a specific table."""
        return self.engine.get_table_schema(db_id, table_name)

    async def get_table_schema_async(self, db_id: str, table_name: str) -> str:
        """Get the schema and sample data for a specific table asynchronously."""
        return await asyncio.to_thread(self.engine.get_table_schema, db_id, table_name)

    def execute(
        self,
        db_id: str,
        sql: str,
        params: Sequence[str | int] | Mapping[str, int | str] | None = None,
        read_only: bool = True,
        max_rows: int = 1000,
    ) -> list[dict[str, Any]]:
        """Execute a SQL query and return results."""
        return self.engine.execute(
            db_id,
            sql,
            params=params,
            read_only=read_only,
            max_rows=max_rows,
        )

    async def execute_async(
        self,
        db_id: str,
        sql: str,
        params: Sequence[str | int] | Mapping[str, int | str] | None = None,
        read_only: bool = True,
        max_rows: int = 1000,
    ) -> list[dict[str, Any]]:
        """Execute a SQL query asynchronously."""
        return await asyncio.to_thread(
            self.engine.execute,
            db_id,
            sql,
            params=params,
            read_only=read_only,
            max_rows=max_rows,
        )

    def get_formatted_db_list(self) -> str:
        """Retrieve list of available databases in markdown format."""
        header = '## AVAILABLE DATABASE REGISTRY\n'
        entries: list[str] = []
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
