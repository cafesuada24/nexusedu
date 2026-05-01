"""Metric repository interface."""

from typing import Any, Protocol


class MetricsRepository(Protocol):
    """Interface for system-wide performance metrics."""

    async def get_kpi_stats(self) -> dict[str, Any]:
        """Calculate high-level KPI stats."""
        ...

    async def get_retention_trend(self) -> list[dict[str, Any]]:
        """Retrieve retention trend data over time."""
        ...
