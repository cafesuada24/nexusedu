"""Query handlers for metrics-related operations."""

from src.application.dtos.metrics_dtos import KPIStatsDTO, RetentionTrendDTO
from src.domain.repositories.metrics_repository import MetricsRepository


class MetricsQueryHandler:
    """Handler for metrics-related queries."""

    def __init__(self, metrics_repo: MetricsRepository):
        self.metrics_repo = metrics_repo

    async def handle_get_kpi_stats(self) -> KPIStatsDTO:
        """Execute the get KPI stats query."""
        stats = await self.metrics_repo.get_kpi_stats()
        return KPIStatsDTO(**stats)

    async def handle_get_retention_trend(self) -> list[RetentionTrendDTO]:
        """Execute the get retention trend query."""
        trend = await self.metrics_repo.get_retention_trend()
        return [RetentionTrendDTO(**item) for item in trend]
