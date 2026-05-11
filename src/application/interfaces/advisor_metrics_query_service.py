"""Advisor metrics query service interface."""

from typing import Protocol

from src.application.dtos.advisor_dtos import PersonalAdvisorMetricsDTO
from src.core.identifiers import EntityID


class AdvisorMetricsQueryService(Protocol):
    """Advisor metrics query service interface."""

    async def get_advisor_metrics(
        self,
        advisor_id: EntityID,
    ) -> PersonalAdvisorMetricsDTO:
        """Calculate and retrieve personal performance metrics for an advisor."""
        ...
