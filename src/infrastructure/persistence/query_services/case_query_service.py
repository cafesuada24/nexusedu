"""Case query service implementation."""

from uuid import UUID

from sqlalchemy import Select, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.case_dtos import CaseDTO, QueryAppointmentDTO, QueryEmailDTO
from src.application.dtos.pagination import PagedResponse, PaginationMetadata
from src.domain.services.gamification import GamificationService
from src.domain.value_objects.status import (
    InterventionStatus,
    MeetingMethod,
    RiskStatus,
)
from src.infrastructure.database.models import Advisor as OrmAdvisor
from src.infrastructure.database.models import Appointment as OrmAppointment
from src.infrastructure.database.models import Case as OrmCase
from src.infrastructure.database.models import InterventionEmail as OrmEmail
from src.infrastructure.database.models import Student as OrmStudent


class SqlAlchemyCaseQueryService:
    """Case Query Service SqlAlchemy implementation."""

    def __init__(
        self,
        session: AsyncSession,
        gamification_service: GamificationService,
    ) -> None:
        """Initialize with a SQLAlchemy async session."""
        self.session = session
        self.gamification_service = gamification_service

    async def find_assigned_to(
        self,
        advisor_id: UUID | None,
        limit: int,
        offset: int,
    ) -> PagedResponse[CaseDTO]:
        """Find cases that have been assigned to an advisor."""
        stmt = self._get_base_query()

        if advisor_id is None:
            stmt = stmt.where(
                OrmCase.assigned_advisor_id.is_(None),
                OrmCase.intervention_status == InterventionStatus.NEW,
            )
        else:
            stmt = stmt.where(
                OrmCase.assigned_advisor_id == advisor_id,
                OrmCase.intervention_status != InterventionStatus.NEW,
            )

        return await self._execute_and_map(stmt, limit, offset)

    async def find_all(
        self,
        limit: int,
        offset: int,
    ) -> PagedResponse[CaseDTO]:
        """Find all cases."""
        stmt = self._get_base_query()
        return await self._execute_and_map(stmt, limit, offset)

    def _get_base_query(self) -> Select[tuple[OrmCase, OrmAdvisor, OrmEmail, OrmAppointment]]:
        """Build the base select statement for cases."""
        return (
            select(
                OrmCase.case_id,
                OrmCase.sid,
                OrmCase.created_at,
                OrmCase.assigned_advisor_id,
                OrmCase.intervention_status,
                OrmAdvisor.name.label('assigned_to'),
                OrmStudent.student_name,
                OrmStudent.major,
                OrmStudent.current_risk_status,
                OrmStudent.email,
                OrmStudent.email.label('student_email'),
                OrmEmail.subject.label('draft_subject'),
                OrmEmail.body.label('draft_body'),
                OrmEmail.status.label('draft_status'),
                OrmEmail.email_id,
                OrmEmail.sent_at,
                OrmAppointment.appointment_time,
                OrmAppointment.duration_minutes,
                OrmAppointment.meeting_method,
                OrmAppointment.notes,
            )
            .join(OrmStudent, OrmCase.sid == OrmStudent.sid)
            .outerjoin(OrmEmail, OrmCase.case_id == OrmEmail.case_id)
            .outerjoin(OrmAdvisor, OrmCase.assigned_advisor_id == OrmAdvisor.advisor_id)
            .outerjoin(OrmAppointment, OrmCase.case_id == OrmAppointment.case_id)
            .order_by(desc(OrmCase.created_at))
        )

    async def _execute_and_map(
        self,
        stmt: Select[tuple[OrmCase, OrmAdvisor, OrmEmail, OrmAppointment]],
        limit: int,
        offset: int,
    ) -> PagedResponse[CaseDTO]:
        """Execute the query and map results to CaseDTOs."""
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.session.execute(count_stmt)
        total_count = count_result.scalar() or 0

        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)

        mappings = result.mappings().all()

        tasks: list[CaseDTO] = []
        for row in mappings:
            risk_status_val = row['current_risk_status']
            if isinstance(risk_status_val, str):
                try:
                    risk_status = RiskStatus(risk_status_val)
                except ValueError:
                    risk_status = RiskStatus.UNKNOWN
            else:
                risk_status = RiskStatus.UNKNOWN

            intervention_status_val = row['intervention_status']
            if isinstance(intervention_status_val, str):
                try:
                    intervention_status = InterventionStatus(intervention_status_val)
                except ValueError:
                    intervention_status = InterventionStatus.NEW
            else:
                intervention_status = InterventionStatus.NEW

            tasks.append(
                CaseDTO(
                    case_id=row['case_id'],
                    sid=row['sid'],
                    created_at=row['created_at'],
                    assigned_advisor_id=row['assigned_advisor_id'],
                    assigned_to=row['assigned_to'],
                    student_name=row['student_name'],
                    major=row['major'] or 'Unknown',
                    current_risk_status=risk_status,
                    intervention_status=intervention_status,
                    email=QueryEmailDTO(
                        email_id=row['email_id'],
                        recipent=row['student_email'],
                        subject=row['draft_subject'],
                        body=row['draft_body'],
                        status=row['draft_status'],
                        created_at=row['created_at'],
                        sent_at=row['sent_at'],
                    )
                    if row['email_id']
                    else None,
                    appointment=QueryAppointmentDTO(
                        appointment_time=row['appointment_time'],
                        duration_minutes=row['duration_minutes'],
                        meeting_method=MeetingMethod(row['meeting_method']),
                        notes=row['notes'],
                    )
                    if row['appointment_time']
                    else None,
                ),
            )
        return PagedResponse(
            items=tasks,
            metadata=PaginationMetadata(
                total_count=total_count,
                limit=limit,
                offset=offset,
                has_next=offset + len(tasks) < total_count,
            ),
        )
