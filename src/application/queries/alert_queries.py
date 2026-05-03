"""Query handlers for alert-related operations."""

from dataclasses import dataclass
from typing import Any

from pydantic import UUID4

from src.application.dtos.pagination_dtos import PagedResult, PaginationMetadata
from src.application.dtos.student_dtos import AlertDTO, EmailDTO, StudentDTO, TaskDTO
from src.domain.repositories.alert_repository import AlertRepository
from src.domain.repositories.case_repository import CaseRepository
from src.domain.repositories.email_repository import EmailRepository
from src.domain.repositories.job_repository import JobRepository
from src.domain.repositories.student_repository import StudentRepository
from src.domain.services.gamification import GamificationService
from src.domain.value_objects.status import InterventionStatus, RiskStatus


@dataclass
class GetActiveAlertsQuery:
    """Query to retrieve active alerts."""

    status_filter: str | None = None
    limit: int = 20
    offset: int = 0


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


class AlertQueryHandler:
    """Handler for alert-related queries."""

    def __init__(
        self,
        alert_repo: AlertRepository,
        email_repo: EmailRepository,
        student_repo: StudentRepository,
        job_repo: JobRepository,
        case_repo: CaseRepository,
    ):
        self.alert_repo = alert_repo
        self.email_repo = email_repo
        self.student_repo = student_repo
        self.job_repo = job_repo
        self.case_repo = case_repo

    async def handle_get_active_alerts(
        self, query: GetActiveAlertsQuery
    ) -> PagedResult[AlertDTO]:
        """Execute the get active alerts query."""
        domain_alerts, total_count = await self.alert_repo.get_active_alerts(
            query.status_filter, limit=query.limit, offset=query.offset
        )

        dtos = []
        for a in domain_alerts:
            # Check for active case
            active_case = await self.case_repo.get_active_case(a.student.sid)
            
            is_generating = False
        return PagedResult(
            items=[
                AlertDTO(
                    student=StudentDTO(
                        sid=alert.student.sid,
                        student_name=alert.student.student_name,
                        email=alert.student.email,
                        major=alert.student.major,
                        current_risk_status=alert.student.current_risk_status,
                        intervention_status=alert.student.intervention_status,
                        last_notified_at=alert.student.last_notified_at,
                        is_generating=alert.student.is_generating,
                        active_case_id=alert.student.active_case_id,
                    ),
                    alert_details={
                        "latest_draft_subject": alert.latest_draft_subject,
                        "latest_draft_body": alert.latest_draft_body,
                    },
                )
                for alert in domain_alerts
            ],
            metadata=PaginationMetadata(
                total_count=total_count,
                limit=query.limit,
                offset=query.offset,
                has_next=(query.offset + query.limit) < total_count,
            ),
        )

    async def handle_get_task_list(self, query: GetTaskListQuery) -> PagedResult[TaskDTO]:
        """Execute the get task list query."""
        gamification = GamificationService()
        raw_tasks, total_count = await self.case_repo.get_task_list(
            advisor_id=query.advisor_id, limit=query.limit, offset=query.offset
        )
        
        return PagedResult(
            items=[
                TaskDTO(
                    case_id=task.case_id,
                    created_at=task.created_at,
                    assigned_advisor_id=task.assigned_advisor_id,
                    student_name=task.student_name,
                    email=task.email,
                    major=task.major,
                    current_risk_status=task.current_risk_status,
                    intervention_status=task.intervention_status,
                    draft_subject=task.draft_subject,
                    draft_body=task.draft_body,
                    draft_status=task.draft_status,
                    assigned_to=task.assigned_to,
                    suggested_action=gamification.get_suggested_action(
                        task.current_risk_status, task.intervention_status
                    ),
                    points_reward=gamification.calculate_points(
                        task.current_risk_status, task.intervention_status
                    ),
                )
                for task in raw_tasks
            ],
            metadata=PaginationMetadata(
                total_count=total_count,
                limit=query.limit,
                offset=query.offset,
                has_next=(query.offset + query.limit) < total_count,
            ),
        )

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
            'resolved_at': case.resolved_at.isoformat() if case.resolved_at else None,
            'email': {
                'email_id': str(email.email_id),
                'subject': email.subject,
                'body': email.body,
                'status': email.status.value,
                'created_at': email.created_at.isoformat(),
                'sent_at': email.sent_at.isoformat() if email.sent_at else None,
            } if email else None
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
