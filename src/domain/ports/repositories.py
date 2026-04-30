"""Port definitions (interfaces) for database repositories."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from datetime import datetime

    from src.database.models import Advisor, Student


class StudentRepository(Protocol):
    """Interface for student-related data operations."""

    async def get_by_id(self, sid: str) -> Student | None:
        """Retrieve a student by their unique ID."""
        ...

    async def get_pii(self, sid: str) -> dict[str, Any] | None:
        """Retrieve student PII (name and email)."""
        ...

    async def update_intervention_status(self, sid: str, status: str) -> None:
        """Update the intervention status for a student."""
        ...

    async def update_draft_job_id(self, sid: str, job_id: str | None) -> None:
        """Update the draft job ID for a student."""
        ...

    async def batch_update_draft_job_ids(self, updates: list[tuple[str, str]]) -> None:
        """Batch update draft job IDs for multiple students."""
        ...

    async def get_latest_status_timestamp(self, sid: str) -> datetime | None:
        """Retrieve the latest status recording timestamp for a student."""
        ...

    async def get_recent_performance(
        self, sid: str, limit: int = 4
    ) -> list[dict[str, Any]]:
        """Retrieve recent performance history for a student."""
        ...

    async def ingest_students(self, records: list[dict[str, Any]]) -> None:
        """Bulk ingest student records."""
        ...

    async def update_risk_status(
        self, sid: str, risk_status: str, intervention_status: str | None = None
    ) -> None:
        """Update the risk and optionally intervention status for a student."""
        ...

    async def update_last_notified(self, sid: str) -> None:
        """Update the last notified timestamp for a student."""
        ...


class ActivityRepository(Protocol):
    """Interface for assessment activity operations."""

    async def ingest_activities(self, records: list[dict[str, Any]]) -> None:
        """Bulk ingest activity records."""
        ...

    async def get_weekly_averages(self) -> list[dict[str, Any]]:
        """Retrieve average scores per student per week."""
        ...


class StatusHistoryRepository(Protocol):
    """Interface for student status history operations."""

    async def create_history_record(self, record: dict[str, Any]) -> None:
        """Create a new status history record."""
        ...

    async def batch_create_history(self, records: list[dict[str, Any]]) -> None:
        """Bulk create status history records."""
        ...

    async def get_all_history(self) -> list[dict[str, Any]]:
        """Retrieve all status history records."""
        ...

    async def get_latest_anomaly(self, sid: str) -> str | None:
        """Get the most recent anomaly flag for a student."""
        ...


class AdvisorRepository(Protocol):
    """Interface for advisor-related data operations."""

    async def get_by_id(self, advisor_id: str) -> Advisor | None:
        """Retrieve an advisor by their unique ID."""
        ...

    async def get_engagement_metrics(self) -> list[dict[str, Any]]:
        """Retrieve aggregated engagement metrics by major."""
        ...

    async def get_leaderboard(self, time_window: str) -> list[dict[str, Any]]:
        """Retrieve the advisor leaderboard for a specific time window."""
        ...

    async def record_points(
        self,
        advisor_id: str,
        sid: str,
        action_type: str,
        points: int,
    ) -> None:
        """Record gamification points for an advisor action."""
        ...


class IdempotencyRepository(Protocol):
    """Interface for idempotency key management."""

    async def check_key(self, key: str) -> bool:
        """Check if an idempotency key exists."""
        ...

    async def record_key(self, key: str) -> None:
        """Record a new idempotency key."""
        ...


class EmailRepository(Protocol):
    """Interface for managing intervention emails."""

    async def get_latest_draft(self, sid: str) -> dict[str, Any] | None:
        """Retrieve the latest draft email for a student."""
        ...

    async def create_draft(
        self,
        sid: str,
        advisor_id: str | None,
        subject: str,
        body: str,
    ) -> str:
        """Create a new draft email and return its ID."""
        ...

    async def mark_as_sent(self, sid: str, body: str) -> None:
        """Mark the latest draft as sent for a student."""
        ...

    async def get_history(self, sid: str) -> list[dict[str, Any]]:
        """Retrieve the communication history for a student."""
        ...


class AlertRepository(Protocol):
    """Interface for managing student alerts."""

    async def get_active_alerts(
        self, status_filter: str | None = None
    ) -> list[dict[str, Any]]:
        """Retrieve students with active alerts for the Kanban board."""
        ...


class MetricsRepository(Protocol):
    """Interface for system-wide performance metrics."""

    async def get_kpi_stats(self) -> dict[str, Any]:
        """Calculate high-level KPI stats."""
        ...

    async def get_retention_trend(self) -> list[dict[str, Any]]:
        """Retrieve retention trend data over time."""
        ...


class MetadataRepository(Protocol):
    """Interface for retrieving database metadata."""

    async def list_tables(self, db_id: str) -> list[str]:
        """List tables in the database."""
        ...

    async def get_table_schema(self, db_id: str, table_name: str) -> str:
        """Get schema for a table."""
        ...

    async def execute_raw(self, db_id: str, sql: str) -> list[dict[str, Any]]:
        """Execute a raw SQL query (for analysis)."""
        ...
