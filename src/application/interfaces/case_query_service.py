"""Case query service interface."""

from typing import Protocol
from uuid import UUID

from src.application.dtos.case_dtos import CaseDTO


class CaseQueryService(Protocol):
    """Query Service for Case."""

    async def find_assigned_to(
        self,
        advisor_id: UUID | None,
        limit: int,
        offset: int,
    ) -> tuple[list[CaseDTO], int]:
        """Find cases that have been assigned to an advisor."""
        ...
