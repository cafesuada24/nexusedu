"""Application service for email-related workflows."""

from datetime import UTC, datetime
from uuid import UUID

import structlog

from src.application.interfaces.unit_of_work import UnitOfWork
from src.application.services.gamification_application_service import (
    GamificationApplicationService,
)
from src.core.identifiers import EntityID
from src.domain.services.email_sending import EmailSendingService
from src.domain.services.gamification import GamificationService

logger = structlog.get_logger(__name__)


class EmailApplicationService:
    """Orchestrates email-related workflows."""

    def __init__(
        self,
        uow: UnitOfWork,
        email_sending_service: EmailSendingService,
        gamification_app_service: GamificationApplicationService,
        gamification_service: GamificationService,
    ) -> None:
        """Initialize with dependencies."""
        self.uow = uow
        self.email_sending_service = email_sending_service
        self.gamification_app_service = gamification_app_service
        self.gamification_service = gamification_service

    async def send_intervention_email(
        self,
        case_id: UUID,
        job_id: EntityID,
        user_id: EntityID,
    ) -> None:
        """Send an intervention email to a student and update records."""
        case = await self.uow.cases.get_by_id(case_id=case_id)
        if not case or not case.assigned_advisor_id:
            logger.error('case_has_no_advisor_or_not_found', case_id=str(case_id))
            return

        email = await self.uow.emails.get_by_case(case_id)
        student = await self.uow.students.get_by_id(case.sid)

        logger.info(
            'dispatching_intervention_email',
            case_id=str(case_id),
            email=student.email,
        )

        await self.email_sending_service.send_email(
            to_email=student.email,
            subject=email.subject,
            body=email.body,
        )

        # 2. Update state atomically
        async with self.uow:
            # Re-fetch entities within the transaction to ensure latest version
            case = await self.uow.cases.get_by_id(case_id)
            email = await self.uow.emails.get_by_case(case_id)
            student = await self.uow.students.get_by_id(case.sid)

            student.last_notified_timestamp = datetime.now(UTC)
            await self.uow.students.save(student)

            email.mark_as_sent()
            await self.uow.emails.save(email)

            case.record_email_sent(job_id=job_id, user_id=user_id)
            await self.uow.cases.save(case)

            # 3. Gamification
            await self.gamification_app_service.award_points(
                advisor_id=case.assigned_advisor_id,
                case_id=case.case_id,
                action=self.gamification_service.Action.SEND_EMAIL,
                occurred_at=datetime.now(UTC),
                base_timestamp=case.assigned_at,
                risk_level=student.current_risk_status,
            )

            await self.uow.commit()

    async def send_review_email(
        self,
        target_email: str,
        subject: str,
        body: str,
    ) -> None:
        """Send a review email."""
        logger.info(
            'dispatching_review_email',
            email=target_email,
        )
        await self.email_sending_service.send_email(
            to_email=target_email,
            subject=subject,
            body=body,
        )
