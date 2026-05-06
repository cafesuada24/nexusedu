"""Ledger query service interface."""

from datetime import datetime
from typing import Protocol
from uuid import UUID


class PointLedgerQueryService(Protocol):
    """Query Service for Point Ledger."""

    async def award_points(
        self,
        advisor_id: UUID,
        task_id: UUID,
        points: int,
        earned_at: datetime,
    ): ...
