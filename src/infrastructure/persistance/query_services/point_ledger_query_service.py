"""Ledger query service implementation."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import PointLedger


class SqlAlchemyPointLedgerQueryService:
    """SqlAlchemy implementation for Point Ledger queries."""

    def __init__(self, session: AsyncSession) -> None:
        self.__session = session

    async def get_total_points(self, advisor_id: UUID) -> int:
        """Calculates total points for an advisor."""
        stmt = (
            select(func.sum(PointLedger.points))
            .where(PointLedger.advisor_id == advisor_id)
        )
        result = await self.__session.execute(stmt)
        return result.scalar() or 0
