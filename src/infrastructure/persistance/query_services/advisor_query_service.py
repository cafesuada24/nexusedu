"""Advisor Query Service implementation.."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import PointLedger


class SqlAlchemyAdvisorQueryService:
    """Sql Alchemy implementation for advisor query service."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_advisor_points(self, advisor_id: UUID) -> int:
        """Calculate advisor accumulated points."""
        stmt = select(func.coalesce(func.sum(PointLedger.points), 0)).where(
            PointLedger.advisor_id == advisor_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0
