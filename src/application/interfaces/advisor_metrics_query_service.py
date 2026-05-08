"""Advisor metrics query service interface."""

from typing import Protocol
from uuid import UUID

from src.application.dtos.advisor_dtos import PersonalAdvisorMetricsDTO


class AdvisorMetricsQueryService(Protocol):
    """Advisor metrics query service interface."""

    async def get_advisor_metrics(
        self,
        advisor_id: UUID,
    ) -> PersonalAdvisorMetricsDTO:
        """Calculate and retrieve personal performance metrics for an advisor."""
        ...
