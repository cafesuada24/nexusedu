"""Ledger query service interface."""

from datetime import datetime
from typing import Protocol
from uuid import UUID


class PointLedgerQueryService(Protocol):
    """Query Service for Point Ledger (Read-only)."""

    async def get_total_points(self, advisor_id: UUID) -> int:
        """Calculates total points for an advisor."""
        ...
