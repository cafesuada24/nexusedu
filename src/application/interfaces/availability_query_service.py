"""Advisor availability query service interface."""

from datetime import date, datetime
from typing import Protocol
from uuid import UUID


class AdvisorAvailabilityQueryService(Protocol):
    """Service to directly query the database for advisor availability slots."""

    async def get_available_slots(
        self,
        advisor_id: UUID,
        start_date: date,
        end_date: date,
        slot_duration_minutes: int = 30,
    ) -> list[datetime]:
        """Directly calculate available UTC timeslots without domain entities."""
        ...
