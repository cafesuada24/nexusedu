"""Query handlers for alert-related operations."""

from dataclasses import dataclass
from typing import List, Optional

from src.application.dtos.student_dtos import AlertDTO, StudentDTO
from src.domain.repositories.interfaces import AlertRepository


@dataclass
class GetActiveAlertsQuery:
    """Query to retrieve active alerts."""

    status_filter: Optional[str] = None


class AlertQueryHandler:
    """Handler for alert-related queries."""

    def __init__(self, alert_repo: AlertRepository):
        self.alert_repo = alert_repo

    async def handle_get_active_alerts(
        self, query: GetActiveAlertsQuery
    ) -> List[AlertDTO]:
        """Execute the get active alerts query."""
        domain_alerts = await self.alert_repo.get_active_alerts(query.status_filter)

        # Map domain alerts to DTOs
        return [
            AlertDTO(
                student=StudentDTO(
                    sid=a.student.sid,
                    name=a.student.name,
                    email=a.student.email,
                    major=a.student.major,
                    current_risk_status=a.student.current_risk_status,
                    intervention_status=a.student.intervention_status,
                    last_notified_timestamp=a.student.last_notified_timestamp,
                ),
                alert_details=a.alert_details,
            )
            for a in domain_alerts
        ]
