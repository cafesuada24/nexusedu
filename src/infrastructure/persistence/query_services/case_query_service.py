"""Case query service implementation."""
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.case_dtos import CaseDTO, QueryEmailDTO
from src.domain.services.gamification import GamificationService
from src.domain.value_objects.status import InterventionStatus, RiskStatus
from src.infrastructure.database.models import Advisor as OrmAdvisor
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
    ) -> tuple[list[CaseDTO], int]:
        """Find cases that have been assigned to an advisor."""
        stmt = (
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
            )
            .join(OrmStudent, OrmCase.sid == OrmStudent.sid)
            .outerjoin(OrmEmail, OrmCase.case_id == OrmEmail.case_id)
            .outerjoin(OrmAdvisor, OrmCase.assigned_advisor_id == OrmAdvisor.advisor_id)
            .order_by(desc(OrmCase.created_at))
        )

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
                    assigned_advisor_id=advisor_id,
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
                    ) if row['email_id'] else None,
                ),
            )
        return tasks, total_count
