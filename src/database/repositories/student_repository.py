"""Repository for student-related database operations."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.database.manager import DatabaseManager


class StudentRepository:
    """Repository for student-related database operations."""

    def __init__(self, db_manager: 'DatabaseManager') -> None:
        """Initialize the repository with a database manager."""
        self.db = db_manager

    async def get_student_pii(self, sid: str) -> dict[str, Any] | None:
        """Retrieve student name and email."""
        results = await self.db.execute_async(
            'sis_db',
            'SELECT student_name, email FROM students WHERE sid = ?',
            (sid,),
        )
        return results[0] if results and 'error' not in results[0] else None

    async def get_latest_status_timestamp(self, sid: str) -> str | None:
        """Retrieve the latest status recording timestamp for a student."""
        results = await self.db.execute_async(
            'sis_db',
            'SELECT status_recorded_at FROM student_status_history WHERE sid = ? ORDER BY status_recorded_at DESC LIMIT 1',
            (sid,),
        )
        return results[0]['status_recorded_at'] if results and 'error' not in results[0] else None

    async def update_intervention_status(self, sid: str, status: str) -> None:
        """Update student intervention status."""
        await self.db.execute_async(
            'sis_db',
            'UPDATE students SET intervention_status = ? WHERE sid = ?',
            (status, sid),
            read_only=False,
        )
