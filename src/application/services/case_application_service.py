"""Application service for case-related workflows."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
import structlog

from src.application.dtos.worker_payloads.case_payloads import AutoResolveCasePayload
from src.application.dtos.worker_payloads.email_payloads import (
    DispatchReviewEmailPayload,
)
from src.application.exceptions import ConfigurationError
from src.application.interfaces.background_queue import BackgroundTaskQueue
from src.application.interfaces.unit_of_work import UnitOfWork
from src.core.config import config

logger = structlog.get_logger(__name__)


class CaseApplicationService:
    """Orchestrates case-related workflows."""

    def __init__(
        self,
        uow: UnitOfWork,
        task_queue: BackgroundTaskQueue,
    ) -> None:
        """Initialize with dependencies."""
        self.uow = uow
        self.task_queue = task_queue

    async def initiate_case_review(
        self,
        case_id: UUID,
    ) -> None:
        """Handle the process of requesting a case review from a student."""
        logger.info('initiating_case_review_process', case_id=str(case_id))

        case = await self.uow.cases.get_by_id(case_id)
        student = await self.uow.students.get_by_id(case.sid)

        # 1. Generate JWT token
        if not config.jwt_secret or config.jwt_secret == 'insecure_default':
            raise ConfigurationError("JWT secret not configured for review tokens")

        jwt_payload = {
            'case_id': str(case_id),
            'exp': datetime.now(UTC) + timedelta(days=7),
            'iat': datetime.now(UTC),
        }
        token = jwt.encode(
            jwt_payload,
            config.jwt_secret,
            algorithm='HS256',
        )

        # 2. Prepare and Dispatch email via task queue
        review_link = config.review_url_template.format(token=token)
        email_body = (
            f'Hi {student.student_name},\n\n'
            f'Your advisor has marked your case as resolved. '
            f'Please take a moment to review the support you received: {review_link}\n\n'
            f'Thank you!'
        )

        await self.task_queue.enqueue(
            'run_dispatch_review_email_task',
            payload=DispatchReviewEmailPayload(
                case_id=case_id,
                header='Review support',
                body=email_body,
                target_email=student.email,
            ),
        )

        # 3. Schedule auto-resolution after 7 days
        await self.task_queue.enqueue(
            'run_auto_resolve_case_task',
            payload=AutoResolveCasePayload(case_id=case_id),
            _defer_by=timedelta(days=7),
        )
