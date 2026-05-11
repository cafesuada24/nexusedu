"""Case query service interface."""

from typing import Protocol

from src.application.dtos.case_dtos import CaseDTO
from src.application.dtos.pagination import PagedResponse
from src.core.identifiers import EntityID


class CaseQueryService(Protocol):
    """Query Service for Case."""

    async def find_assigned_to(
        self,
        advisor_id: EntityID | None,
        limit: int,
        offset: int,
    ) -> PagedResponse[CaseDTO]:
        """Find cases that have been assigned to an advisor."""
        ...

    async def find_all(
        self,
        limit: int,
        offset: int,
    ) -> PagedResponse[CaseDTO]:
        """Find all cases."""
        ...
