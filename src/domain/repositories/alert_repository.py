"""Alert reporsitory interface."""

from typing import Protocol

from src.domain.entities.alert import Alert


class AlertRepository(Protocol):
    """Interface for managing student alerts."""

    async def get_active_alerts(
        self,
        status_filter: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Alert], int]:
        """Retrieve students with active alerts for the Kanban board with pagination.
        
        Returns:
            Tuple of (list of alerts, total count)
        """
        ...
