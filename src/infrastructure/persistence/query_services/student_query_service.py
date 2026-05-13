"""Student query service implementation."""

from uuid import UUID

from sqlalchemy import cast, desc, func, select, Double
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.pagination import PagedResponse, PaginationMetadata
from src.application.dtos.student_dtos import (
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
        # 1. Term-level aggregation with window functions for previous averages
        # Subquery to aggregate by term first
        term_agg = (
            select(
                Activity.academic_year,
                Activity.semester,
                func.avg(Activity.score).label('term_avg'),
                func.sum(Activity.score).label('term_sum'),
                func.count(Activity.score).label('term_cnt'),
            )
            .where(Activity.sid == sid)
            .group_by(Activity.academic_year, Activity.semester)
            .cte('term_agg')
        )

        # Window functions for cumulative previous sum and count
        prev_sum = func.sum(term_agg.c.term_sum).over(
            order_by=[term_agg.c.academic_year, term_agg.c.semester],
            rows=(None, -1),  # UNBOUNDED PRECEDING AND 1 PRECEDING
        )
        prev_cnt = func.sum(term_agg.c.term_cnt).over(
            order_by=[term_agg.c.academic_year, term_agg.c.semester],
            rows=(None, -1),
        )

        metrics_stmt = select(
            term_agg.c.academic_year,
            term_agg.c.semester,
            term_agg.c.term_avg,
            (prev_sum / cast(prev_cnt, Double)).label('prev_avg'),
        )

        if academic_year:
            metrics_stmt = metrics_stmt.where(term_agg.c.academic_year == academic_year)
        if semester:
            metrics_stmt = metrics_stmt.where(term_agg.c.semester == semester)

        metrics_stmt = metrics_stmt.order_by(
            term_agg.c.academic_year.desc(),
            term_agg.c.semester.desc(),
        )

        metrics_res = await self.session.execute(metrics_stmt)
        term_metrics_rows = metrics_res.all()

        # 2. Get course metrics for all relevant terms in one query
        courses_stmt = (
            select(
                Activity.academic_year,
                Activity.semester,
                Activity.course_id,
                Activity.course_name,
                func.avg(Activity.score).label('avg_score'),
            )
            .where(Activity.sid == sid)
        )
        if academic_year:
            courses_stmt = courses_stmt.where(Activity.academic_year == academic_year)
        if semester:
            courses_stmt = courses_stmt.where(Activity.semester == semester)

        courses_stmt = courses_stmt.group_by(
            Activity.academic_year,
            Activity.semester,
            Activity.course_id,
            Activity.course_name,
        )

        courses_res = await self.session.execute(courses_stmt)
        course_rows = courses_res.all()

        # Group courses by term for easy lookup
        courses_by_term: dict[tuple[int, int], list[TermCourseMetricsDTO]] = {}
        for c in course_rows:
            key = (c.academic_year, c.semester)
            if key not in courses_by_term:
                courses_by_term[key] = []
            courses_by_term[key].append(
                TermCourseMetricsDTO(
                    course_id=c.course_id,
                    course_name=c.course_name,
                    avg_score=c.avg_score,
                ),
            )

        # Assemble DTOs
        term_dtos: list[TermMetricsDTO] = [
            TermMetricsDTO(
                academic_year=m.academic_year,
                semester=m.semester,
                term_avg_score=m.term_avg,
                previous_terms_avg_score=m.prev_avg,
                courses=courses_by_term.get((m.academic_year, m.semester), []),
            )
            for m in term_metrics_rows
        ]

        return StudentTermMetricsDTO(
            sid=sid,
            terms=term_dtos,
        )
