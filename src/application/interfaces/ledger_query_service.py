"""Ledger query service interface."""

from typing import Protocol

from src.core.identifiers import EntityID


class PointLedgerQueryService(Protocol):
    """Query Service for Point Ledger (Read-only)."""

    async def get_total_points(self, advisor_id: EntityID) -> int:
        """Calculates total points for an advisor."""
        ...
