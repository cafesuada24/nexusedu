"""Command handlers for alert-related operations."""

from dataclasses import dataclass
from typing import Optional

from src.domain.repositories.interfaces import StudentRepository
from src.domain.value_objects.status import InterventionStatus


@dataclass
class UpdateStudentStatusCommand:
    """Command to update a student's intervention status."""

    sid: str
    status: InterventionStatus
    user_id: str


class AlertCommandHandler:
    """Handler for alert-related commands."""

    def __init__(self, student_repo: StudentRepository):
        self.student_repo = student_repo

    async def handle_update_status(self, command: UpdateStudentStatusCommand) -> None:
        """Execute the status update command."""
        await self.student_repo.update_intervention_status(command.sid, command.status)
        # Note: Gamification points logic will be moved here or to a domain service
