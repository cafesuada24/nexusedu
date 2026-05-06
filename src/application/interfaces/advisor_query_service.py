"""Advisor query service interface."""

from typing import Protocol
from uuid import UUID


class AdvisorQueryService(Protocol):
    """Advisor query service interface."""

    async def get_advisor_points(self, advisor_id: UUID) -> int:
        """Calculate advisor accumulated points."""
        ...
