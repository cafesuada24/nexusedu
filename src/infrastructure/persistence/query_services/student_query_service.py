"""Student query service implementation."""

from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.pagination import PagedResponse, PaginationMetadata
from src.application.dtos.student_dtos import StudentDTO
from src.domain.value_objects.status import InterventionStatus
from src.infrastructure.database.models import Case as OrmCase
from src.infrastructure.database.models import Student as OrmStudent


class SqlAlchemyStudentQueryService:
    """Student Query Service SqlAlchemy implementation."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a SQLAlchemy async session."""
        self.session = session

    async def get_all_students(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> PagedResponse[StudentDTO]:
        """Retrieve a paginated list of students."""
        # Join with the most recent open case if it exists
        # We use a subquery or outer join to get an active case
        stmt = (
            select(
                OrmStudent,
                OrmCase.case_id.label('active_case_id'),
                OrmCase.intervention_status,
            )
            .outerjoin(
                OrmCase,
                (OrmStudent.sid == OrmCase.sid)
                & (
                    OrmCase.intervention_status.in_(
                        [
                            InterventionStatus.NEW,
                            InterventionStatus.ACCEPTED,
                            InterventionStatus.SENT,
                            InterventionStatus.BOOKED,
                            InterventionStatus.SUPPORTING,
                            InterventionStatus.PENDING_REVIEW,
                        ],
                    )
                ),
            )
            .order_by(desc(OrmStudent.last_notified_timestamp), OrmStudent.student_name)
        )

        count_stmt = select(func.count()).select_from(OrmStudent)
        total_count_result = await self.session.execute(count_stmt)
        total_count = total_count_result.scalar() or 0

        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)

        students: list[StudentDTO] = []
        for row in result.all():
            orm_student = row[0]
            active_case_id = row[1]
            intervention_status = row[2]

            students.append(
                StudentDTO(
                    sid=orm_student.sid,
                    student_name=orm_student.student_name,
                    email=orm_student.email,
                    major=orm_student.major,
                    current_risk_status=orm_student.current_risk_status,
                    intervention_status=intervention_status,
                    last_notified_at=orm_student.last_notified_timestamp,
                    active_case_id=active_case_id,
                    is_generating=False,
                ),
            )

        return PagedResponse(
            items=students,
            metadata=PaginationMetadata(
                total_count=total_count,
                limit=limit,
                offset=offset,
                has_next=offset + len(students) < total_count,
            ),
        )

    async def get_student(self, sid: UUID) -> StudentDTO:
        """Retrieve a single student by ID."""
        stmt = (
            select(
                OrmStudent,
                OrmCase.case_id.label('active_case_id'),
                OrmCase.intervention_status,
            )
            .outerjoin(
                OrmCase,
                (OrmStudent.sid == OrmCase.sid)
                & (
                    OrmCase.intervention_status.in_(
                        [
                            InterventionStatus.NEW,
                            InterventionStatus.ACCEPTED,
                            InterventionStatus.SENT,
                            InterventionStatus.BOOKED,
                            InterventionStatus.SUPPORTING,
                            InterventionStatus.PENDING_REVIEW,
                        ],
                    )
                ),
            )
            .where(OrmStudent.sid == sid)
        )

        result = await self.session.execute(stmt)
        row = result.first()

        if not row:
            raise ValueError(f'Student with ID {sid} not found')

        orm_student = row[0]
        active_case_id = row[1]
        intervention_status = row[2]

        return StudentDTO(
            sid=orm_student.sid,
            student_name=orm_student.student_name,
            email=orm_student.email,
            major=orm_student.major,
            current_risk_status=orm_student.current_risk_status,
            intervention_status=intervention_status,
            last_notified_at=orm_student.last_notified_timestamp,
            active_case_id=active_case_id,
            is_generating=False,
        )
