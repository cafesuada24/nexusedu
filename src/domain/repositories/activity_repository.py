"""Activity repository interface."""

from typing import Any, Protocol


class ActivityRepository(Protocol):
    """Interface for assessment activity operations."""

    async def ingest_activities(self, records: list[dict[str, Any]]) -> None:
        """Bulk ingest activity records."""
        ...

    async def get_weekly_averages(self) -> list[dict[str, Any]]:
        """Retrieve average scores per student per week."""
        ...
