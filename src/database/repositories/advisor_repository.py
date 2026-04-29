"""Repository for advisor-related database operations."""

import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.database.manager import DatabaseManager


class AdvisorRepository:
    """Repository for advisor-related database operations."""

    def __init__(self, db_manager: 'DatabaseManager') -> None:
        """Initialize the repository with a database manager."""
        self.db = db_manager

    async def get_advisor(self, advisor_id: str) -> dict[str, Any] | None:
        """Retrieve advisor details by ID."""
        results = await self.db.execute_async(
            'sis_db',
            'SELECT advisor_id, name, email FROM advisors WHERE advisor_id = ?',
            (advisor_id,),
        )
        return results[0] if results and 'error' not in results[0] else None

    async def record_points(self, advisor_id: str, sid: str, action_type: str, points: int) -> None:
        """Record points for an advisor in the ledger."""
        ledger_id = str(uuid.uuid4())
        await self.db.execute_async(
            'sis_db',
            'INSERT INTO advisor_points_ledger (id, advisor_id, action_type, points, sid) VALUES (?, ?, ?, ?, ?)',
            (ledger_id, advisor_id, action_type, points, sid),
            read_only=False,
        )
