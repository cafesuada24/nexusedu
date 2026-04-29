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

    def update_draft_job_ids(self, updates: list[tuple[str, str]]) -> None:
        """Update the draft_job_id for multiple students.

        Args:
            updates: List of (job_id, sid) tuples.
        """
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
        params: Sequence[str | int] | Mapping[str, int | str] | None = None,
        read_only: bool = True,
        max_rows: int = 1000,
    ) -> list[dict[str, Any]]:
        """Execute a SQL query and return results."""
        ...

    def update_intervention_status(self, sid: str, status: str) -> None:
        """Update the intervention lifecycle status for a specific student."""
        ...

    def inject_points(self, advisor_id: str, sid: str, action_type: str) -> None:
        """Inject points for an advisor action into the points ledger."""
        ...

    def check_idempotency(self, key: str) -> bool:
        """Check if an idempotency key has already been used."""
        ...

    def record_idempotency(self, key: str) -> None:
        """Record an idempotency key."""

    def check_health(self) -> dict[str, str]:
        """Verify connectivity to all registered databases."""
        ...

    def close(self) -> None:
        """Close any open resources."""
        ...

class AnomalyAlgorithm(Protocol):
    """Protocol for anomaly detection algorithms."""

    def run(self, engine: DatabaseEngine) -> list[str]:
        """Run the anomaly detection and update history.

        Returns:
            List of student IDs (SIDs) whose status transitioned to 'new'.
        """
        ...
