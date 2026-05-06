"""Ledger query service interface."""

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import PointLedger


class SqlAlchemyPointLedgerQueryService:
    """SqlAlchemy implementation for Point Ledger."""

    def __init__(self, session: AsyncSession) -> None:

        self.__session = session

    async def award_points(
        self,
        advisor_id: UUID,
        task_id: UUID,
        points: int,
        earned_at: datetime,
    ):
        if points <= 0:
            raise ValueError('Points must be positive.')

        record = PointLedger(
            advisor_id=advisor_id,
            task_id=task_id,
            points=points,
            earned_at=earned_at,
        )

        self.__session.add(record)
