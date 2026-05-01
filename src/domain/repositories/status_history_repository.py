"""Status history repository interface."""

from typing import Any, Protocol
from uuid import UUID

from src.domain.value_objects.status import RiskStatus


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

    async def get_latest_anomaly(self, sid: UUID) -> RiskStatus | None:
        """Get the most recent anomaly flag for a student."""
        ...
