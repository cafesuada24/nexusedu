"""Student query service implementation."""

from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.pagination import PagedResponse, PaginationMetadata
from src.application.dtos.student_dtos import (
    CaseOverviewDTO,
    StudentDTO,
    StudentTermMetricsDTO,
    TermCourseMetricsDTO,
    TermMetricsDTO,
)
from src.domain.value_objects.status import InterventionStatus
from src.infrastructure.database.models import Activity
from src.infrastructure.database.models import Case as OrmCase
from src.infrastructure.database.models import Student as OrmStudent


class SqlAlchemyStudentQueryService:
    """Student Query Service SqlAlchemy implementation."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a SQLAlchemy async session."""
        self.session = session

    async def _get_active_case_overview(self, sid: UUID) -> CaseOverviewDTO | None:
        """Helper to fetch AI overview from the student's latest active case."""
        stmt = (
            select(OrmCase.academic_summary, OrmCase.action_keys)
            .where(
                OrmCase.sid == sid,
                OrmCase.intervention_status.in_(
                    [
                        InterventionStatus.NEW,
                        InterventionStatus.ACCEPTED,
                        InterventionStatus.SENT,
                        InterventionStatus.BOOKED,
                        InterventionStatus.SUPPORTING,
                        InterventionStatus.PENDING_REVIEW,
                    ],
                ),
            )
            .order_by(OrmCase.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        row = result.first()

        if row and row.academic_summary:
            return CaseOverviewDTO(
                academic_summary=row.academic_summary,
                action_keys=row.action_keys or [],
            )
        return None

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

    async def get_student_term_metrics(
        self,
        sid: UUID,
        academic_year: int | None = None,
        semester: int | None = None,
    ) -> StudentTermMetricsDTO:
        """Retrieve term-based metrics and course details for a student."""
        # 1. Identify all terms for the student
        term_stmt = (
            select(
                Activity.academic_year,
                Activity.semester,
            )
            .where(Activity.sid == sid)
            .distinct()
        )
        if academic_year:
            term_stmt = term_stmt.where(Activity.academic_year == academic_year)
        if semester:
            term_stmt = term_stmt.where(Activity.semester == semester)

        term_stmt = term_stmt.order_by(
            Activity.academic_year.desc(),
            Activity.semester.desc(),
        )

        terms_res = await self.session.execute(term_stmt)
        terms = terms_res.all()

        term_dtos: list[TermMetricsDTO] = []
        for t_yr, t_sem in terms:
            # 2. Get term average
            term_avg_stmt = select(func.avg(Activity.score)).where(
                Activity.sid == sid,
                Activity.academic_year == t_yr,
                Activity.semester == t_sem,
            )
            term_avg = (await self.session.execute(term_avg_stmt)).scalar() or 0.0

            # 3. Get previous terms average
            prev_avg_stmt = select(func.avg(Activity.score)).where(
                Activity.sid == sid,
                (Activity.academic_year < t_yr)
                | ((Activity.academic_year == t_yr) & (Activity.semester < t_sem)),
            )
            prev_avg = (await self.session.execute(prev_avg_stmt)).scalar()

            # 4. Get courses in this term
            courses_stmt = (
                select(
                    Activity.course_id,
                    Activity.course_name,
                    func.avg(Activity.score).label('avg_score'),
                )
                .where(
                    Activity.sid == sid,
                    Activity.academic_year == t_yr,
                    Activity.semester == t_sem,
                )
                .group_by(Activity.course_id, Activity.course_name)
            )
            courses_res = await self.session.execute(courses_stmt)
            course_dtos = [
                TermCourseMetricsDTO(
                    course_id=c.course_id,
                    course_name=c.course_name,
                    avg_score=c.avg_score,
                )
                for c in courses_res.all()
            ]

            term_dtos.append(
                TermMetricsDTO(
                    academic_year=t_yr,
                    semester=t_sem,
                    term_avg_score=term_avg,
                    previous_terms_avg_score=prev_avg,
                    courses=course_dtos,
                ),
            )

        ai_overview = await self._get_active_case_overview(sid)

        return StudentTermMetricsDTO(
            sid=sid,
            terms=term_dtos,
            ai_overview=ai_overview,
        )
