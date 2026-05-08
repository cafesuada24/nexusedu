"""Gamification query service implementation."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.gamification_dtos import (
    LeaderboardEntryDTO,
)
from src.application.dtos.pagination import PagedResponse, PaginationMetadata
from src.domain.value_objects.gamification import RankingType
from src.infrastructure.database.models import Advisor, PointLedger


class SqlAlchemyGamificationQueryService:
    """SqlAlchemy implementation for Gamification query service."""

    def __init__(self, session: AsyncSession) -> None:
        self.__session = session

    async def get_leaderboard(
        self,
        time_window: RankingType,
        limit: int = 10,
        offset: int = 0,
    ) -> PagedResponse[LeaderboardEntryDTO]:
        """Get the current leaderboard."""
        interval_map = {
            RankingType.WEEKLY: timedelta(days=7),
            RankingType.MONTHLY: timedelta(days=30),
            RankingType.SEMESTER: timedelta(days=120),
        }

        # Calculate cutoff if needed
        cutoff = None
        if time_window != RankingType.ALL_TIME and time_window in interval_map:
            cutoff = datetime.now(UTC) - interval_map[time_window]

        ledger_join_cond = Advisor.advisor_id == PointLedger.advisor_id
        if cutoff:
            ledger_join_cond = and_(ledger_join_cond, PointLedger.earned_at >= cutoff)

        stmt = (
            select(
                Advisor.advisor_id,
                Advisor.name,
                func.coalesce(func.sum(PointLedger.points), 0).label('total_points'),
                func.count(PointLedger.id).label('actions_count'),
                func.count(
                    case((PointLedger.action == 'send_email', 1)),
                ).label('sent_count'),
                func.count(
                    case((PointLedger.action == 'resolve_case', 1)),
                ).label('resolved_count'),
            )
            .outerjoin(PointLedger, ledger_join_cond)
            .group_by(
                Advisor.advisor_id,
                Advisor.name,
            )
            .order_by(desc('total_points'))
        )

        # Count total items (total number of advisors)
        count_stmt = select(func.count(Advisor.advisor_id))
        count_result = await self.__session.execute(count_stmt)
        total_count = count_result.scalar() or 0

        # Apply paging
        stmt = stmt.limit(limit).offset(offset)
        result = await self.__session.execute(stmt)

        entries = [
            LeaderboardEntryDTO(
                advisor_id=row.advisor_id,
                name=row.name,
                total_points=row.total_points,
                actions_count=row.actions_count,
                sent_count=row.sent_count,
                resolved_count=row.resolved_count,
            )
            for row in result.all()
        ]

        return PagedResponse(
            items=entries,
            metadata=PaginationMetadata(
                total_count=total_count,
                limit=limit,
                offset=offset,
                has_next=(offset + limit) < total_count,
            ),
        )
