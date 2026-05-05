"""Query handlers for alert-related operations."""

from dataclasses import dataclass
from typing import Any

from pydantic import UUID4

from src.application.dtos.student_dtos import AlertDTO, EmailDTO, StudentDTO
from src.domain.repositories.alert_repository import AlertRepository
from src.domain.repositories.email_repository import EmailRepository
from src.domain.repositories.student_repository import StudentRepository
from src.presentation.dtos.pagination import PagedResponse, PaginationMetadata


@dataclass
class GetActiveAlertsQuery:
    """Query to retrieve active alerts."""

    status_filter: str | None = None
    limit: int = 20
    offset: int = 0


class AlertQueryHandler:
    """Handler for alert-related queries."""

    def __init__(
        self,
        alert_repo: AlertRepository,
        email_repo: EmailRepository,
        student_repo: StudentRepository,
    ):
        self.alert_repo = alert_repo
        self.email_repo = email_repo
        self.student_repo = student_repo

    async def handle_get_active_alerts(
        self, query: GetActiveAlertsQuery
    ) -> PagedResponse[AlertDTO]:
        """Execute the get active alerts query."""
        domain_alerts, total_count = await self.alert_repo.get_active_alerts(
            query.status_filter, limit=query.limit, offset=query.offset
        )

        return PagedResponse[AlertDTO](
            items=[
                AlertDTO(
                    student=StudentDTO(
                        sid=alert.student.sid,
                        student_name=alert.student.student_name,
                        email=alert.student.email,
                        major=alert.student.major,
                        current_risk_status=alert.student.current_risk_status,
                        intervention_status=alert.student.intervention_status,
                        last_notified_at=alert.student.last_notified_timestamp,
                        is_generating=False,
                        active_case_id=None,
                    ),
                    alert_details={
                        "latest_draft_subject": alert.alert_details.get("draft_subject"),
                        "latest_draft_body": alert.alert_details.get("draft_body"),
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
