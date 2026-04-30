"""Service layer for Dashboard Metrics and KPIs."""

from typing import Any

from src.domain.ports.repositories import MetricsRepository
from src.telemetry.logger import logger


class MetricsService:
    """Service for calculating system-wide performance metrics."""

    def __init__(self, metrics_repo: MetricsRepository) -> None:
        """Initialize the MetricsService.

        Args:
            metrics_repo: Repository for metric operations.
        """
        self.metrics_repo = metrics_repo

    async def get_kpi_stats(self) -> dict[str, Any]:
        """Calculate high-level KPI stats for the dashboard.

        Returns:
            Dictionary with retention_rate, total_interventions, advisor_engagement, and dropout_rate.
        """
        try:
            return await self.metrics_repo.get_kpi_stats()
        except Exception as e:
            logger.error(f'Error calculating KPI stats: {e}')
            raise

    async def get_retention_trend(self) -> list[dict[str, Any]]:
        """Retrieve retention trend data over time (weeks).

        Returns:
            List of data points for the trend chart.
        """
        try:
            return await self.metrics_repo.get_retention_trend()
        except Exception as e:
            logger.error(f'Error calculating retention trend: {e}')
            raise
