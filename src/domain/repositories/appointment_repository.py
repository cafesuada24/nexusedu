"""Appointment repository interface."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.domain.entities.appointment import Appointment


class AppointmentRepository(Protocol):
    """Interface for managing student-advisor appointments."""

    async def add(self, appointment: Appointment) -> None:
        """Add a new appointment."""
        ...

    async def save(self, appointment: Appointment) -> None:
        """Update an existing appointment."""
        ...

    async def get_by_case(self, case_id: UUID) -> Appointment:
        """Find the appointment associated with a specific case."""
        ...

    async def find_by_case(self, case_id: UUID) -> Appointment | None:
        """Retrieve the appointment associated with a specific case."""
        ...

    async def list_by_advisor_and_range(
        self,
        advisor_id: UUID,
        from_dt: datetime,
        to_dt: datetime,
    ) -> list[Appointment]:
        """List appointments for an advisor within a datetime range [from_dt, to_dt)."""
        ...
