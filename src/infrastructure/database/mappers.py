"""Mappers between SQLAlchemy ORM models and Domain Entities."""

from datetime import UTC, datetime
from uuid import UUID

from src.domain.entities.advisor import Advisor as DomainAdvisor
from src.domain.entities.alert import Alert as DomainAlert
from src.domain.entities.case import Case as DomainCase
from src.domain.entities.intervention_email import (
    InterventionEmail as DomainInterventionEmail,
)
from src.domain.entities.student import Student as DomainStudent
from src.domain.entities.task import Task as DomainTask
from src.domain.value_objects.status import (
    CaseStatus,
    EmailStatus,
    InterventionStatus,
    RiskStatus,
    TaskStatus,
    TaskType,
)
from src.infrastructure.database.models import (
    Advisor as OrmAdvisor,
)
from src.infrastructure.database.models import (
    Case as OrmCase,
)
from src.infrastructure.database.models import (
    InterventionEmail as OrmInterventionEmail,
)
from src.infrastructure.database.models import (
    Student as OrmStudent,
)
from src.infrastructure.database.models import (
    Task as OrmTask,
)


class DataMapper:
    """Static mapping methods for domain-infrastructure conversion."""

    @staticmethod
    def to_domain_student(orm_student: OrmStudent) -> DomainStudent:
        """Map ORM Student to Domain Student."""
        return DomainStudent(
            sid=orm_student.sid,
            student_name=orm_student.student_name,
            email=orm_student.email,
            major=orm_student.major,
            current_risk_status=RiskStatus(orm_student.current_risk_status),
            intervention_status=InterventionStatus(orm_student.intervention_status),
            last_notified_timestamp=orm_student.last_notified_timestamp,
            last_notified_satisfaction=orm_student.last_notified_satisfaction,
        )

    @staticmethod
    def to_domain_advisor(orm_advisor: OrmAdvisor) -> DomainAdvisor:
        """Map ORM Advisor to Domain Advisor."""
        return DomainAdvisor(
            advisor_id=orm_advisor.advisor_id,
            name=orm_advisor.name,
            email=orm_advisor.email,
            user_id=orm_advisor.user_id,
        )

    @staticmethod
    def to_domain_email(orm_email: OrmInterventionEmail) -> DomainInterventionEmail:
        """Map ORM InterventionEmail to Domain InterventionEmail."""
        return DomainInterventionEmail(
            email_id=orm_email.email_id,
            sid=orm_email.sid,
            case_id=orm_email.case_id,
            advisor_id=orm_email.advisor_id,
            subject=orm_email.subject,
            body=orm_email.body,
            status=EmailStatus(orm_email.status),
            created_at=orm_email.created_at,
            sent_at=orm_email.sent_at,
        )

    @staticmethod
    def to_domain_case(orm_case: OrmCase) -> DomainCase:
        """Map ORM Case to Domain Case."""
        domain_case = DomainCase(
            case_id=orm_case.case_id,
            sid=orm_case.sid,
            status=orm_case.status,
            created_at=orm_case.created_at,
            closed_at=orm_case.closed_at,
            assigned_advisor_id=orm_case.assigned_advisor_id,
        )
        if hasattr(orm_case, 'tasks') and orm_case.tasks:
            domain_case.tasks = [DataMapper.to_domain_task(t) for t in orm_case.tasks]
        return domain_case

    @staticmethod
    def to_domain_task(orm_task: OrmTask) -> DomainTask:
        """Map ORM Task to Domain Task."""
        return DomainTask(
            task_id=orm_task.task_id,
            case_id=orm_task.case_id,
            action_type=TaskType(orm_task.action_type),
            status=TaskStatus(orm_task.status),
            points_reward=orm_task.points_reward,
            created_at=orm_task.created_at,
            completed_at=orm_task.completed_at,
            completed_by_advisor_id=orm_task.completed_by_advisor_id,
        )

    @staticmethod
    def to_domain_alert(
        orm_student: OrmStudent,
        alert_details: dict[str, object],
    ) -> DomainAlert:
        """Map ORM Student and details to Domain Alert."""
        student = DataMapper.to_domain_student(orm_student)
        return DomainAlert(
            id=student.sid,
            student=student,
            alert_details=alert_details,
            created_at=datetime.now(UTC),
        )
