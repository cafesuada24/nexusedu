"""Mappers between SQLAlchemy ORM models and Domain Entities."""

from uuid import UUID

from src.domain.entities.advisor import Advisor as DomainAdvisor
from src.domain.entities.appointment import (
    Appointment as DomainAppointment,
)
from src.domain.entities.case import Case as DomainCase
from src.domain.entities.intervention_email import (
    InterventionEmail as DomainInterventionEmail,
)
from src.domain.entities.job import Job as DomainJob
from src.domain.entities.point_ledger import (
    PointLedger as DomainLedger,
)
from src.domain.entities.point_ledger import (
    PointLedgerEntry as DomainLedgerEntry,
)
from src.domain.entities.schedule import DayOff as DomainDayOff
from src.domain.entities.schedule import WorkingHours as DomainWorkingHours
from src.domain.entities.student import Student as DomainStudent
from src.domain.value_objects.status import (
    EmailStatus,
    MeetingMethod,
    RiskStatus,
)
from src.infrastructure.database.models import (
    Advisor as OrmAdvisor,
)
from src.infrastructure.database.models import (
    AdvisorDayOff as OrmDayOff,
)
from src.infrastructure.database.models import (
    AdvisorWorkingHours as OrmWorkingHours,
)
from src.infrastructure.database.models import (
    Appointment as OrmAppointment,
)
from src.infrastructure.database.models import (
    BackgroundJobTracker,
)
from src.infrastructure.database.models import (
    Case as OrmCase,
)
from src.infrastructure.database.models import (
    InterventionEmail as OrmInterventionEmail,
)
from src.infrastructure.database.models import (
    PointLedger as OrmLedger,
)
from src.infrastructure.database.models import (
    Student as OrmStudent,
)


class DataMapper:
    """Static mapping methods for domain-infrastructure conversion."""

    @staticmethod
    def to_domain_ledger(
        advisor_id: UUID,
        orm_entries: list[OrmLedger],
    ) -> DomainLedger:
        """Map ORM PointLedger records to Domain PointLedger aggregate."""
        entries = [
            DomainLedgerEntry(
                id=entry.id,
                advisor_id=entry.advisor_id,
                case_id=entry.case_id,
                action=entry.action,
                points=entry.points,
                earned_at=entry.earned_at,
            )
            for entry in orm_entries
        ]
        return DomainLedger(advisor_id=advisor_id, entries=entries)

    @staticmethod
    def to_orm_ledger(domain_entry: DomainLedgerEntry) -> OrmLedger:
        """Map Domain PointLedgerEntry to ORM PointLedger."""
        return OrmLedger(
            id=domain_entry.id,
            advisor_id=domain_entry.advisor_id,
            case_id=domain_entry.case_id,
            action=domain_entry.action,
            points=domain_entry.points,
            earned_at=domain_entry.earned_at,
        )

    @staticmethod
    def to_domain_student(orm_student: OrmStudent) -> DomainStudent:
        """Map ORM Student to Domain Student."""
        return DomainStudent(
            sid=orm_student.sid,
            student_name=orm_student.student_name,
            email=orm_student.email,
            major=orm_student.major,
            current_risk_status=RiskStatus(orm_student.current_risk_status),
            last_notified_timestamp=orm_student.last_notified_timestamp,
            last_notified_satisfaction=orm_student.last_notified_satisfaction,
        )

    @staticmethod
    def to_domain_working_hours(orm_wh: OrmWorkingHours) -> DomainWorkingHours:
        """Map ORM WorkingHours to Domain WorkingHours."""
        return DomainWorkingHours(
            id=orm_wh.id,
            advisor_id=orm_wh.advisor_id,
            day_of_week=orm_wh.day_of_week,
            start_time=orm_wh.start_time,
            end_time=orm_wh.end_time,
            timezone=orm_wh.timezone,
        )

    @staticmethod
    def to_orm_working_hours(domain_wh: DomainWorkingHours) -> OrmWorkingHours:
        """Map Domain WorkingHours to ORM WorkingHours."""
        return OrmWorkingHours(
            id=domain_wh.id,
            advisor_id=domain_wh.advisor_id,
            day_of_week=domain_wh.day_of_week,
            start_time=domain_wh.start_time,
            end_time=domain_wh.end_time,
            timezone=domain_wh.timezone,
        )

    @staticmethod
    def to_domain_day_off(orm_do: OrmDayOff) -> DomainDayOff:
        """Map ORM DayOff to Domain DayOff."""
        return DomainDayOff(
            id=orm_do.id,
            advisor_id=orm_do.advisor_id,
            date=orm_do.date,
            reason=orm_do.reason,
        )

    @staticmethod
    def to_orm_day_off(domain_do: DomainDayOff) -> OrmDayOff:
        """Map Domain DayOff to ORM DayOff."""
        return OrmDayOff(
            id=domain_do.id,
            advisor_id=domain_do.advisor_id,
            date=domain_do.date,
            reason=domain_do.reason,
        )

    @staticmethod
    def to_domain_advisor(orm_advisor: OrmAdvisor) -> DomainAdvisor:
        """Map ORM Advisor to Domain Advisor."""
        return DomainAdvisor(
            advisor_id=orm_advisor.advisor_id,
            name=orm_advisor.name,
            email=orm_advisor.email,
            user_id=orm_advisor.user_id,
            title=orm_advisor.title,
            phone=orm_advisor.phone,
            faculty=orm_advisor.faculty,
            office=orm_advisor.office,
            bio=orm_advisor.bio,
        )

    @staticmethod
    def to_domain_email(orm_email: OrmInterventionEmail) -> DomainInterventionEmail:
        """Map ORM InterventionEmail to Domain InterventionEmail."""
        return DomainInterventionEmail(
            email_id=orm_email.email_id,
            case_id=orm_email.case_id,
            subject=orm_email.subject,
            body=orm_email.body,
            status=EmailStatus(orm_email.status),
            created_at=orm_email.created_at,
            sent_at=orm_email.sent_at,
            version=orm_email.version,
        )

    @staticmethod
    def to_domain_appointment(orm_appointment: OrmAppointment) -> DomainAppointment:
        """Map ORM Appointment to Domain Appointment."""
        return DomainAppointment(
            appointment_id=orm_appointment.appointment_id,
            case_id=orm_appointment.case_id,
            appointment_time=orm_appointment.appointment_time,
            duration_minutes=orm_appointment.duration_minutes,
            meeting_method=MeetingMethod(orm_appointment.meeting_method),
            notes=orm_appointment.notes,
            created_at=orm_appointment.created_at,
        )

    @staticmethod
    def to_orm_appointment(domain_appointment: DomainAppointment) -> OrmAppointment:
        """Map Domain Appointment to ORM Appointment."""
        return OrmAppointment(
            appointment_id=domain_appointment.appointment_id,
            case_id=domain_appointment.case_id,
            appointment_time=domain_appointment.appointment_time,
            duration_minutes=domain_appointment.duration_minutes,
            meeting_method=domain_appointment.meeting_method,
            notes=domain_appointment.notes,
            created_at=domain_appointment.created_at,
        )

    @staticmethod
    def to_domain_case(orm_case: OrmCase) -> DomainCase:
        """Map ORM Case to Domain Case."""
        return DomainCase(
            case_id=orm_case.case_id,
            sid=orm_case.sid,
            intervention_status=orm_case.intervention_status,
            created_at=orm_case.created_at,
            closed_at=orm_case.closed_at,
            assigned_at=orm_case.assigned_at,
            assigned_advisor_id=orm_case.assigned_advisor_id,
            version=orm_case.version,
            appointment=DataMapper.to_domain_appointment(orm_case.appointment)
            if orm_case.appointment
            else None,
        )

    @staticmethod
    def to_orm_case(domain_case: DomainCase) -> OrmCase:
        """Map Domain Case to ORM Case."""
        return OrmCase(
            case_id=domain_case.case_id,
            sid=domain_case.sid,
            intervention_status=domain_case.intervention_status,
            created_at=domain_case.created_at,
            assigned_at=domain_case.assigned_at,
            closed_at=domain_case.closed_at,
            version=domain_case.version,
            assigned_advisor_id=domain_case.assigned_advisor_id,
            appointment=DataMapper.to_orm_appointment(domain_case.appointment)
            if domain_case.appointment
            else None,
        )

    @staticmethod
    def to_domain_job(orm_case: BackgroundJobTracker) -> DomainJob:
        """Map ORM Case to Domain Case."""
        return DomainJob(
            job_id=orm_case.job_id,
            created_at=orm_case.created_at,
            correlation_id=orm_case.correlation_id,
            correlation_type=orm_case.correlation_type,
            status=orm_case.status,
            started_at=orm_case.started_at,
            ended_at=orm_case.completed_at,
        )
