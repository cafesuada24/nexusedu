"""Mappers between SQLAlchemy ORM models and Domain Entities."""

from typing import Any, Dict

from src.domain.entities.advisor import Advisor as DomainAdvisor
from src.domain.entities.alert import Alert as DomainAlert
from src.domain.entities.intervention_email import (
    InterventionEmail as DomainInterventionEmail,
)
from src.domain.entities.student import Student as DomainStudent
from src.domain.value_objects.status import EmailStatus, InterventionStatus, RiskStatus
from src.infrastructure.database.models import (
    Advisor as OrmAdvisor,
)
from src.infrastructure.database.models import (
    InterventionEmail as OrmInterventionEmail,
)
from src.infrastructure.database.models import (
    Student as OrmStudent,
)


class DataMapper:
    """Static mapping methods for domain-infrastructure conversion."""

    @staticmethod
    def to_domain_student(orm_student: OrmStudent) -> DomainStudent:
        """Map ORM Student to Domain Student."""
        return DomainStudent(
            sid=orm_student.sid,
            name=orm_student.student_name,
            email=orm_student.email,
            major=orm_student.major,
            current_risk_status=RiskStatus(orm_student.current_risk_status),
            intervention_status=InterventionStatus(orm_student.intervention_status),
            last_notified_timestamp=orm_student.last_notified_timestamp,
            last_notified_satisfaction=orm_student.last_notified_satisfaction,
            draft_job_id=orm_student.draft_job_id,
        )

    @staticmethod
    def to_domain_advisor(orm_advisor: OrmAdvisor) -> DomainAdvisor:
        """Map ORM Advisor to Domain Advisor."""
        return DomainAdvisor(
            advisor_id=orm_advisor.advisor_id,
            name=orm_advisor.name,
            email=orm_advisor.email,
        )

    @staticmethod
    def to_domain_email(orm_email: OrmInterventionEmail) -> DomainInterventionEmail:
        """Map ORM InterventionEmail to Domain InterventionEmail."""
        return DomainInterventionEmail(
            email_id=orm_email.email_id,
            sid=orm_email.sid,
            advisor_id=orm_email.advisor_id,
            subject=orm_email.subject,
            body=orm_email.body,
            status=EmailStatus(orm_email.status),
            created_at=orm_email.created_at,
            sent_at=orm_email.sent_at,
        )

    @staticmethod
    def to_domain_alert(orm_student: OrmStudent, alert_details: Dict[str, Any]) -> DomainAlert:
        """Map ORM Student and details to Domain Alert."""
        student = DataMapper.to_domain_student(orm_student)
        return DomainAlert(
            student=student,
            alert_details=alert_details,
        )
