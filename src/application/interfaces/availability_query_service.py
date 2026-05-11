"""Advisor availability query service interface."""

from datetime import date, datetime
from typing import Protocol

from src.application.dtos.advisor_dtos import AdvisorScheduleDTO
from src.core.identifiers import EntityID


class AdvisorAvailabilityQueryService(Protocol):
    """Service to directly query the database for advisor availability slots."""

    async def get_available_slots(
        self,
        advisor_id: EntityID,
        start_date: date,
        end_date: date,
        slot_duration_minutes: int = 30,
    ) -> list[datetime]:
        """Directly calculate available UTC timeslots without domain entities."""
        ...

    async def get_advisor_schedule(self, advisor_id: EntityID) -> AdvisorScheduleDTO:
        """Fetch the full schedule directly from the database."""
        ...
