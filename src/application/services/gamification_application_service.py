"""Application service for coordinating gamification workflows."""

from datetime import datetime
from uuid import UUID

import structlog

from src.application.interfaces.background_queue import BackgroundTaskQueue
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.services.gamification import GamificationService
from src.domain.value_objects.status import RiskStatus
from src.domain.value_objects.student_satisfaction import StudentSatisfaction

logger = structlog.get_logger(__name__)


class GamificationApplicationService:
    """Orchestrates gamification logic across domain services and repositories."""

    def __init__(
        self,
        uow: UnitOfWork,
        gamification_service: GamificationService,
        task_queue: BackgroundTaskQueue | None = None,
    ) -> None:
        """Initialize the service."""
        self.uow = uow
        self.gamification_service = gamification_service
        self.task_queue = task_queue

    async def award_points(
        self,
        advisor_id: UUID,
        case_id: UUID,
        action: GamificationService.Action,
        occurred_at: datetime,
        base_timestamp: datetime | None,
        risk_level: RiskStatus,
        satisfaction: StudentSatisfaction | None = None,
    ) -> int:
        """Calculate and award points to an advisor."""
        points = self.gamification_service.calculate_points(
            action_type=action,
            recorded_dt=base_timestamp,
            risk_level=risk_level,
            satisfaction=satisfaction,
        )

        ledger = await self.uow.point_ledger.get_by_advisor_id(advisor_id)
        ledger.award_points(
            case_id=case_id,
            action=str(action),
            points=points,
            earned_at=occurred_at,
        )
        await self.uow.point_ledger.save(ledger)

        logger.info(
            "points_awarded",
            advisor_id=str(advisor_id),
            case_id=str(case_id),
            action=str(action),
            points=points,
        )

        return points

    async def evaluate_advisor_badges(self, advisor_id: UUID) -> list[str]:
        """Check and award new badges for an advisor."""
        stats = await self.uow.badges.get_advisor_stats(advisor_id)
        eligible_badges = self.gamification_service.check_badges(stats)
        existing_badges = await self.uow.badges.get_advisor_badges(advisor_id)

        new_badges = []
        for badge in eligible_badges:
            if badge not in existing_badges:
                await self.uow.badges.award_badge(advisor_id, badge)
                new_badges.append(badge)

        if new_badges:
            logger.info(
                "new_badges_awarded",
                advisor_id=str(advisor_id),
                badges=new_badges,
            )

        return new_badges
