"""Query handlers for alert-related operations."""

from dataclasses import dataclass
from typing import Any

from pydantic import UUID4

from src.application.dtos.student_dtos import AlertDTO, EmailDTO, StudentDTO
from src.domain.repositories.alert_repository import AlertRepository
from src.domain.repositories.case_repository import CaseRepository
from src.domain.repositories.email_repository import EmailRepository
from src.domain.repositories.job_repository import JobRepository
from src.domain.repositories.student_repository import StudentRepository


@dataclass
class GetActiveAlertsQuery:
    """Query to retrieve active alerts."""

    status_filter: str | None = None


@dataclass
class GetEmailHistoryQuery:
    """Query to retrieve communication history for a student."""

    sid: UUID4


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
            
            # Check for active job related to case or student
            correlation_id = active_case.case_id if active_case else a.student.sid
            correlation_type = 'case' if active_case else 'student'
            
            active_job = await self.job_repo.get_active_job(
                correlation_id, correlation_type, 'email_draft'
            )
            
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
                        is_generating=active_job is not None,
                        active_case_id=active_case.case_id if active_case else None,
                    ),
                    alert_details=a.alert_details,
                )
            )
        return dtos

    async def handle_get_email_history(
        self, query: GetEmailHistoryQuery
    ) -> list[EmailDTO]:
        """Execute the get email history query."""
        history = await self.email_repo.get_history(query.sid)
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
            for e in history
        ]

    async def handle_get_draft_status(self, sid: UUID4) -> dict[str, Any]:
        """Retrieve the current AI draft status and content for a student."""
        student = await self.student_repo.get_by_id(sid)
        if not student:
            raise ValueError(f'Student {sid} not found.')

        history = await self.email_repo.get_history(sid)
        latest_draft = next((d for d in history if d.status.value == 'draft'), None)

        active_case = await self.case_repo.get_active_case(sid)
        correlation_id = active_case.case_id if active_case else sid
        correlation_type = 'case' if active_case else 'student'

        active_job = await self.job_repo.get_active_job(
            correlation_id, correlation_type, 'email_draft'
        )

        return {
            'sid': sid,
            'is_generating': active_job is not None,
            'subject': latest_draft.subject if latest_draft else None,
            'body': latest_draft.body if latest_draft else None,
            'active_case_id': str(active_case.case_id) if active_case else None,
        }
