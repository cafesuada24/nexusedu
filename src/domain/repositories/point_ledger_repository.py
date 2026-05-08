"""Point ledger repository interface."""
from typing import Protocol
from uuid import UUID

from src.domain.entities.point_ledger import PointLedger


class PointLedgerRepository(Protocol):
    """Interface for Point Ledger persistence."""

    async def get_by_advisor_id(self, advisor_id: UUID) -> PointLedger:
        """Loads the point ledger for a specific advisor."""
        ...

    async def save(self, ledger: PointLedger) -> None:
        """Persists any changes (new entries) in the ledger."""
        ...
