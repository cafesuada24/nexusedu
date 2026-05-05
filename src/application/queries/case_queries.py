"""Query handlers for case-related operations."""

from dataclasses import dataclass
from typing import Any

from pydantic import UUID4

from src.application.dtos.case_dtos import CaseDTO, TaskDTO
from src.application.dtos.pagination_dtos import PagedResult, PaginationMetadata
from src.application.dtos.student_dtos import EmailDTO
from src.domain.repositories.case_repository import CaseRepository
from src.domain.repositories.email_repository import EmailRepository
from src.domain.repositories.job_repository import JobRepository
from src.domain.repositories.student_repository import StudentRepository
from src.domain.services.gamification import GamificationService
from src.domain.value_objects.status import (
    InterventionStatus,
    RiskStatus,
)


@dataclass
class GetEmailHistoryQuery:
    """Query to retrieve communication history for a student."""

    sid: UUID4


@dataclass
class GetTaskListQuery:
    """Query to retrieve advisor task list."""

    advisor_id: UUID4 | None = None
    limit: int = 20
    offset: int = 0


class CaseQueryHandler:
    """Handler for case-related queries."""

    def __init__(
        self,
        email_repo: EmailRepository,
        student_repo: StudentRepository,
        job_repo: JobRepository,
        case_repo: CaseRepository,
    ):
        self.email_repo = email_repo
        self.student_repo = student_repo
        self.job_repo = job_repo
        self.case_repo = case_repo

    async def handle_get_cases_list(
        self,
        query: GetTaskListQuery,
    ) -> PagedResult[CaseDTO]:
        """Execute the get task list query."""
        gamification = GamificationService()
        raw_cases, total_count = await self.case_repo.get_cases_list(
            advisor_id=query.advisor_id,
            limit=query.limit,
            offset=query.offset,
        )

        return PagedResult(
            items=[
                CaseDTO(
                    case_id=case.case_id,
                    sid=case.sid,
                    created_at=case.created_at,
                    assigned_advisor_id=case.assigned_advisor_id,
                    student_name=case.student_name,
                    email=case.email,
                    major=case.major,
                    current_risk_status=case.current_risk_status,
                    intervention_status=case.intervention_status,
                    draft_subject=case.draft_subject,
                    draft_body=case.draft_body,
                    draft_status=case.draft_status,
                    assigned_to=case.assigned_to,
                    suggested_action=self._get_suggested_action(
                        case.current_risk_status,
                        case.intervention_status,
                    ),
                    points_reward=gamification.calculate_points(
                        GamificationService.Action.SEND_EMAIL,
                        case.created_at,
                        case.current_risk_status,
                    ),
                    tasks=[
                        TaskDTO(
                            task_id=t.task_id,
                            action_type=t.action_type,
                            status=t.status,
                            points_reward=t.points_reward,
                            completed_at=t.completed_at,
                            completed_by_advisor_id=t.completed_by_advisor_id,
                        )
                        for t in case.tasks
                    ]
                    if case.tasks
                    else [],
                )
                for case in raw_cases
            ],
            metadata=PaginationMetadata(
                total_count=total_count,
                limit=query.limit,
                offset=query.offset,
                has_next=(query.offset + query.limit) < total_count,
            ),
        )

    def _get_suggested_action(
        self, risk: RiskStatus, intervention: InterventionStatus
    ) -> str:
        """Helper to determine suggested action."""
        if intervention == InterventionStatus.NOTIFIED:
            return 'Schedule Meeting'
        if risk == RiskStatus.CRITICAL:
            return 'Immediate Outreach'
        return 'Review Draft'

    async def handle_get_email_history(
        self, query: GetEmailHistoryQuery
    ) -> list[EmailDTO]:
        """Execute the get email history query."""
        domain_emails = await self.email_repo.get_history(query.sid)
        return [
            EmailDTO(
                email_id=e.email_id,
                sid=e.sid,
                subject=e.subject,
                body=e.body,
                status=e.status.value,
                created_at=e.created_at.isoformat(),
                sent_at=e.sent_at.isoformat() if e.sent_at else None,
            )
            for e in domain_emails
        ]

    async def handle_get_case_details(self, case_id: UUID4) -> dict[str, Any]:
        """Retrieve full details of a specific case, including its associated email."""
        case = await self.case_repo.get_by_id(case_id)
        if not case:
            raise ValueError(f'Case {case_id} not found.')

        email = await self.email_repo.get_by_case(case_id)

        return {
            'case_id': str(case.case_id),
            'sid': str(case.sid),
            'status': case.status.value,
            'created_at': case.created_at.isoformat(),
            'resolved_at': case.closed_at.isoformat() if case.closed_at else None,
            'email': {
                'email_id': str(email.email_id),
                'subject': email.subject,
                'body': email.body,
                'status': email.status.value,
                'created_at': email.created_at.isoformat(),
                'sent_at': email.sent_at.isoformat() if email.sent_at else None,
            }
            if email
            else None,
        }

    async def handle_get_draft_status(self, case_id: UUID4) -> dict[str, Any]:
        """Retrieve the current AI draft status and content for a case."""
        case = await self.case_repo.get_by_id(case_id)
        if not case:
            raise ValueError(f'Case {case_id} not found.')

        # 1. Look for existing email record for this case
        email = await self.email_repo.get_by_case(case_id)

        is_generating = False
        progress = 0
        subject = None
        body = None

        if email:
            is_generating = email.status.value == 'generating'
            subject = email.subject
            body = email.body

            # 2. If generating, optionally fetch fine-grained progress from JobRepository
            if is_generating:
                active_job = await self.job_repo.get_active_job(
                    case_id, 'case', 'email_draft'
                )
                if active_job:
                    job_details = await self.job_repo.get_job(active_job)
                    if job_details:
                        progress = job_details.get('progress', 0)

        return {
            'sid': str(case.sid),
            'is_generating': is_generating,
            'progress': progress,
            'subject': subject,
            'body': body,
            'active_case_id': str(case.case_id),
        }
