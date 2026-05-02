"""Student repository interface."""

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from src.domain.entities.student import Student
from src.domain.value_objects.status import InterventionStatus, RiskStatus


class StudentRepository(Protocol):
    """Interface for student-related data operations."""

    async def get_by_id(self, sid: UUID) -> Student | None:
        """Retrieve a student by their unique ID."""
        ...

    async def get_pii(self, sid: UUID) -> dict[str, Any] | None:
        """Retrieve student PII (name and email)."""
        ...

    async def update_intervention_status(
        self,
        sid: UUID,
        status: InterventionStatus,
    ) -> None:
        """Update the intervention status for a student."""
        ...

    async def get_latest_status_timestamp(self, sid: UUID) -> datetime | None:
        """Retrieve the latest status recording timestamp for a student."""
        ...

    async def get_recent_performance(
        self,
        sid: UUID,
        limit: int = 4,
    ) -> list[dict[str, Any]]:
        """Retrieve recent performance history for a student."""
        ...

    async def ingest_students(self, records: list[dict[str, Any]]) -> None:
        """Bulk ingest student records."""
        ...

    async def update_risk_status(
        self,
        sid: UUID,
        risk_status: RiskStatus,
        intervention_status: InterventionStatus | None = None,
    ) -> None:
        """Update the risk and optionally intervention status for a student."""
        ...

    async def update_last_notified(self, sid: UUID) -> None:
        """Update the last notified timestamp for a student."""
        ...
