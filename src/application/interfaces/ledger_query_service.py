"""Ledger query service interface."""

from datetime import datetime
from typing import Protocol
from uuid import UUID


class PointLedgerQueryService(Protocol):
    """Query Service for Point Ledger."""

    async def award_points(
        self,
        advisor_id: UUID,
        case_id: UUID,
        action: str,
        points: int,
        earned_at: datetime,
    ): ...
