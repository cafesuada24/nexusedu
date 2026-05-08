"""Gamification query service implementation."""

from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import and_, case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.gamification_dtos import (
    EngagementMetricsEntryDTO,
    LeaderboardEntryDTO,
)
from src.application.dtos.pagination import PagedResponse
from src.domain.value_objects.gamification import RankingType
from src.domain.value_objects.status import InterventionStatus
from src.infrastructure.database.models import Advisor, PointLedger, Student


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
                    case((OrmTask.action_type == 'send email', 1)),
                ).label('sent_count'),
                func.count(
                    case((OrmTask.action_type == 'resolve case', 1)),
                ).label('resolved_count'),
            )
            .outerjoin(PointLedger, ledger_join_cond)
            .outerjoin(OrmTask, PointLedger.task_id == OrmTask.task_id)
        )

        stmt = stmt.group_by(
            Advisor.advisor_id,
            Advisor.name,
        ).order_by(desc('total_points'))

        # Count total items (total number of advisors)
        count_stmt = select(func.count(Advisor.advisor_id))
        count_result = await self.session.execute(count_stmt)
        total_count = count_result.scalar() or 0

        # Apply paging
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return [row._asdict() for row in result.all()], total_count

    async def get_engagement_metrics(self) -> list[EngagementMetricsEntryDTO]:
        """Retrieve aggregated engagement metrics by major."""
        stmt = (
            select(
                Student.major.label('faculty'),
                func.count(
                    case(
                        (
                            Student.intervention_status
                            != InterventionStatus.NONE.value,
                            1,
                        ),
                    ),
                ).label('sent'),
                func.count(
                    case((Student.intervention_status == 'notified', 1)),
                ).label('drafted'),
            )
            .group_by(Student.major)
            .order_by(desc('sent'))
        )

        result = await self.__session.execute(stmt)
        return [
            EngagementMetricsEntryDTO(
                major=row['faculty'],
                sent_count=row['sent'],
                drafted_count=row['drafted'],
            )
            for row in result.mappings().all()
        ]
