"""Query handlers for alert-related operations."""

from dataclasses import dataclass
from typing import Any

from pydantic import UUID4

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


@dataclass
class GetEmailHistoryQuery:
    """Query to retrieve communication history for a student."""

    sid: UUID4


@dataclass
class GetTaskListQuery:
    """Query to retrieve advisor task list."""

    advisor_id: UUID4 | None = None


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
    ) -> list[AlertDTO]:
        """Execute the get active alerts query."""
        domain_alerts = await self.alert_repo.get_active_alerts(query.status_filter)

        dtos = []
        for a in domain_alerts:
            # Check for active case
            active_case = await self.case_repo.get_active_case(a.student.sid)
            
            is_generating = False
            if active_case:
                email = await self.email_repo.get_by_case(active_case.case_id)
                if email:
                    is_generating = email.status.value == 'generating'

            dtos.append(
                AlertDTO(
                    student=StudentDTO(
                        sid=a.student.sid,
                        student_name=a.student.student_name,
                        email=a.student.email,
                        major=a.student.major,
                        current_risk_status=a.student.current_risk_status,
                        intervention_status=a.student.intervention_status,
                        last_notified_at=a.student.last_notified_timestamp,
                        is_generating=is_generating,
                        active_case_id=active_case.case_id if active_case else None,
                    ),
                    alert_details=a.alert_details,
                )
            )
        return dtos

    async def handle_get_task_list(self, query: GetTaskListQuery) -> list[TaskDTO]:
        """Execute the get task list query."""
        gamification = GamificationService()
        raw_tasks = await self.case_repo.get_task_list(advisor_id=query.advisor_id)
        
        dtos = []
        for row in raw_tasks:
            draft_status = row.draft_status
            
            # Determine suggested action
            if draft_status == 'draft':
                suggested_action = "Review & Send Email"
                action_type = 'email_sent'
            elif draft_status == 'generating':
                suggested_action = "Wait for Draft"
                action_type = 'email_sent'
            elif draft_status == 'sent':
                suggested_action = "Follow up"
                action_type = 'student_resolved' # Or another action
            else:
                suggested_action = "Initiate Intervention"
                action_type = 'email_sent'
                
            # Determine points reward based on GamificationService
            points_reward = gamification.calculate_points(
                action_type=action_type,
                recorded_dt=row.created_at,
                risk_level=row.current_risk_status
            )
            
            dtos.append(
                TaskDTO(
                    case_id=row.case_id,
                    created_at=row.created_at,
                    assigned_advisor_id=row.assigned_advisor_id,
                    student_name=row.student_name,
                    email=row.email,
                    major=row.major,
                    current_risk_status=row.current_risk_status,
                    intervention_status=row.intervention_status,
                    draft_subject=row.draft_subject,
                    draft_body=row.draft_body,
                    draft_status=str(draft_status) if draft_status else None,
                    assigned_to=row.assigned_to,
                    suggested_action=suggested_action,
                    points_reward=points_reward,
                )
            )
        return dtos

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
