"""Case query service implementation."""
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.case_dtos import CaseDTO
from src.domain.services.gamification import GamificationService
from src.domain.value_objects.status import CaseStatus, InterventionStatus, RiskStatus
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
                OrmAdvisor.name.label('assigned_to'),
                OrmStudent.student_name,
                OrmStudent.major,
                OrmStudent.current_risk_status,
                OrmStudent.intervention_status,
                OrmStudent.email,
                OrmEmail.subject.label('draft_subject'),
                OrmEmail.body.label('draft_body'),
                OrmEmail.status.label('draft_status'),
            )
            .join(OrmStudent, OrmCase.sid == OrmStudent.sid)
            .outerjoin(OrmEmail, OrmCase.case_id == OrmEmail.case_id)
            .outerjoin(OrmAdvisor, OrmCase.assigned_advisor_id == OrmAdvisor.advisor_id)
            .order_by(desc(OrmCase.created_at))
        )

        if advisor_id is None:
            stmt = stmt.where(
                OrmCase.assigned_advisor_id.is_(None),
                OrmCase.status == CaseStatus.OPEN,
            )
        else:
            stmt = stmt.where(
                OrmCase.assigned_advisor_id == advisor_id,
                OrmCase.status != CaseStatus.OPEN,
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
                    intervention_status = InterventionStatus.NONE
            else:
                intervention_status = InterventionStatus.NONE

            tasks.append(
                CaseDTO(
                    case_id=row['case_id'],
                    sid=row['sid'],
                    created_at=row['created_at'],
                    assigned_advisor_id=advisor_id,
                    assigned_to=row['assigned_to'],
                    student_name=row['student_name'],
                    email=row['email'],
                    major=row['major'] or 'Unknown',
                    current_risk_status=risk_status,
                    intervention_status=intervention_status,
                    draft_subject=row['draft_subject'],
                    draft_body=row['draft_body'],
                    draft_status=row['draft_status'],
                    points_reward=self.gamification_service.calculate_points(
                        GamificationService.Action.SEND_EMAIL,
                        row['created_at'],
                        risk_status,
                    ),
                ),
            )
        return tasks, total_count
