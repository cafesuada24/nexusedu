"""Alert reporsitory interface."""

from typing import Protocol

from src.domain.entities.alert import Alert


class AlertRepository(Protocol):
    """Interface for managing student alerts."""

    async def get_active_alerts(self, status_filter: str | None = None) -> list[Alert]:
        """Retrieve students with active alerts for the Kanban board."""
        ...
