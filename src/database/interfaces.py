"""Protocols defining the core database and algorithm interfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

class DatabaseEngine(Protocol):
    """Protocol for database engines to allow swapping implementations."""

    def initialize_schema(self) -> None:
        """Initialize the database schema for LMS and SIS."""
        ...

    def ingest_records(
        self,
        db_id: str,
        table_name: str,
        records: Sequence[Mapping[str, Any]],
    ) -> None:
        """Ingest a list of dictionaries into a specified table."""
        ...

    def ingest_custom_data(
        self,
        table_name: str,
        records: Sequence[Mapping[str, Any]],
    ) -> None:
        """Dynamically create and ingest custom data."""
        ...

    def list_tables(self, db_id: str) -> list[str]:
        """List all tables in the specified database."""
        ...

    def get_table_schema(self, db_id: str, table_name: str) -> str:
        """Get the schema and sample data for a specific table."""
        ...

    def execute(
        self,
        db_id: str,
        sql: str,
        read_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Execute a SQL query and return results."""
        ...

    def update_intervention_status(self, sid: str, status: str) -> None:
        """Update the intervention lifecycle status for a specific student."""
        ...

    def check_health(self) -> dict[str, str]:
        """Verify connectivity to all registered databases."""
        ...

    def close(self) -> None:
        """Close any open resources."""
        ...

class AnomalyAlgorithm(Protocol):
    """Protocol for anomaly detection algorithms."""

    def run(self, engine: DatabaseEngine) -> None:
        """Run the anomaly detection and update history."""
        ...
