"""SQLAlchemy implementations of the repository ports."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Integer,
    String,
    case,
    cast,
    desc,
    distinct,
    func,
    inspect,
    literal,
    literal_column,
    or_,
    quoted_name,
    select,
    text,
    update,
)
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.application.exceptions import ConcurrencyError
from src.core.config import config
from src.domain.exceptions import (
    AdvisorNotFoundError,
    CaseNotFoundError,
    EmailNotFoundError,
    JobNotFoundError,
    StudentNotFoundError,
    UserIsNotAnAdvisorError,
)
from src.domain.value_objects.status import (
    InterventionStatus,
    RiskStatus,
)
from src.infrastructure.database.config import DB_REGISTRY
from src.infrastructure.database.mappers import DataMapper
from src.infrastructure.database.models import (
    Activity,
    AdvisorBadge,
    BackgroundJobTracker,
    IdempotencyKey,
    InterventionEmail,
    PointLedger,
    Student,
    StudentStatusHistory,
    UserSettings,
)
from src.infrastructure.database.models import Advisor as OrmAdvisor
from src.infrastructure.database.models import Case as OrmCase

if TYPE_CHECKING:
    from sqlalchemy.engine.interfaces import ReflectedColumn
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import Session

    from src.domain.entities.advisor import Advisor as DomainAdvisor
    from src.domain.entities.case import Case as DomainCase
    from src.domain.entities.intervention_email import (
        InterventionEmail as DomainInterventionEmail,
    )
    from src.domain.entities.job import Job
    from src.domain.entities.point_ledger import PointLedger as DomainLedger
    from src.domain.entities.student import Student as DomainStudent
    from src.domain.repositories.metadata_repository import DBDescription
    from src.domain.repositories.point_ledger_repository import PointLedgerRepository


class SqlAlchemyStudentRepository:
    """SQLAlchemy implementation of the StudentRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a SQLAlchemy async session."""
        self.session = session
        self.chunk_size = config.db_ingest_chunk_size

    async def get_by_id(self, sid: uuid.UUID) -> DomainStudent:
        """Retrieve a student by their unique ID."""
        stmt = select(Student).where(Student.sid == sid)
        result = await self.session.execute(stmt)
        student = result.scalar_one_or_none()
        if student is None:
            raise StudentNotFoundError(sid)
        return DataMapper.to_domain_student(student)

    async def save(self, student: DomainStudent) -> None:
        stmt = (
            update(Student)
            .where(Student.sid == student.sid)
            .values(
                student_name=student.student_name,
                email=student.email,
                major=student.major,
                current_risk_status=student.current_risk_status.value,
                last_notified_timestamp=student.last_notified_timestamp,
                last_notified_satisfaction=student.last_notified_satisfaction,
            )
        )
        await self.session.execute(stmt)

    async def get_recent_performance(
        self,
        sid: uuid.UUID,
        limit: int = 4,
    ) -> list[dict[str, Any]]:
        """Retrieve recent performance history for a student."""
        stmt = (
            select(
                StudentStatusHistory.academic_year.label('yr'),
                StudentStatusHistory.semester.label('sem'),
                StudentStatusHistory.week.label('wk'),
                StudentStatusHistory.current_score_avg.label('score'),
                StudentStatusHistory.anomaly_flag.label('status'),
            )
            .where(StudentStatusHistory.sid == sid)
            .order_by(
                desc(StudentStatusHistory.academic_year),
                desc(StudentStatusHistory.semester),
                desc(StudentStatusHistory.week),
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    async def ingest_students(self, records: list[dict[str, Any]]) -> None:
        """Bulk ingest student records using upsert logic."""
        if not records:
            return

        # Ensure UUID fields are actual UUID objects (SQLAlchemy Uuid type requirement)
        for record in records:
            if 'sid' in record and isinstance(record['sid'], str):
                record['sid'] = uuid.UUID(record['sid'])

        # Manual Chunking to avoid "too many variables" error (SQLite limit is ~999)
        # Configurable via DB_INGEST_CHUNK_SIZE env var.
        for i in range(0, len(records), self.chunk_size):
            batch = records[i : i + self.chunk_size]

            # Dynamically choose insert implementation based on dialect
            dialect = self.session.bind.dialect.name if self.session.bind else 'sqlite'
            if dialect == 'postgresql':
                from sqlalchemy.dialects.postgresql import (  # noqa: PLC0415
                    insert as pg_insert,
                )

                stmt = pg_insert(Student).values(batch).on_conflict_do_nothing()
            else:
                stmt = sqlite_insert(Student).values(batch).on_conflict_do_nothing()

            await self.session.execute(stmt)


class SqlAlchemyActivityRepository:
    """SQLAlchemy implementation of the ActivityRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a SQLAlchemy async session."""
        self.session = session
        self.chunk_size = config.db_ingest_chunk_size

    async def ingest_activities(self, records: list[dict[str, Any]]) -> None:
        """Bulk ingest activity records using upsert logic."""
        if not records:
            return
        # Ensure UUID fields are actual UUID objects (SQLAlchemy Uuid type requirement)
        for record in records:
            if not record.get('activity_id'):
                record['activity_id'] = uuid.uuid4()
            elif isinstance(record['activity_id'], str):
                record['activity_id'] = uuid.UUID(record['activity_id'])

            if 'sid' in record and isinstance(record['sid'], str):
                record['sid'] = uuid.UUID(record['sid'])

        # Manual Chunking to avoid "too many variables" error (SQLite limit is ~999)
        # Configurable via DB_INGEST_CHUNK_SIZE env var.
        for i in range(0, len(records), self.chunk_size):
            batch = records[i : i + self.chunk_size]

            # Dynamically choose insert implementation based on dialect
            dialect = self.session.bind.dialect.name if self.session.bind else 'sqlite'
            if dialect == 'postgresql':
                from sqlalchemy.dialects.postgresql import (  # noqa: PLC0415
                    insert as pg_insert,
                )

                stmt = pg_insert(Activity).values(batch).on_conflict_do_nothing()
            else:
                stmt = sqlite_insert(Activity).values(batch).on_conflict_do_nothing()

            await self.session.execute(stmt)

    async def get_weekly_averages(self) -> list[dict[str, Any]]:
        """Retrieve average scores per student per week."""
        stmt = (
            select(
                Activity.sid,
                Activity.academic_year,
                Activity.semester,
                Activity.week,
                func.avg(Activity.score).label('avg_score'),
            )
            .group_by(
                Activity.sid,
                Activity.academic_year,
                Activity.semester,
                Activity.week,
            )
            .order_by(
                Activity.sid,
                Activity.academic_year,
                Activity.semester,
                Activity.week,
            )
        )
        result = await self.session.execute(stmt)
        return [dict(row) for row in result.mappings().all()]


class SqlAlchemyStatusHistoryRepository:
    """SQLAlchemy implementation of the StatusHistoryRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a SQLAlchemy async session."""
        self.session = session

    async def create_history_record(self, record: dict[str, Any]) -> None:
        """Create a new status history record."""
        entry = StudentStatusHistory(**record)
        self.session.add(entry)
        # await self.session.commit() removed

    async def batch_create_history(self, records: list[dict[str, Any]]) -> None:
        """Bulk create status history records."""
        if not records:
            return
        self.session.add_all([StudentStatusHistory(**r) for r in records])
        # await self.session.commit() removed

    async def get_all_history(self) -> list[dict[str, Any]]:
        """Retrieve all status history records ordered for processing."""
        stmt = select(
            StudentStatusHistory.sid,
            StudentStatusHistory.academic_year,
            StudentStatusHistory.semester,
            StudentStatusHistory.week,
        ).order_by(
            StudentStatusHistory.sid,
            StudentStatusHistory.academic_year,
            StudentStatusHistory.semester,
            StudentStatusHistory.week,
        )
        result = await self.session.execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    async def get_latest_anomaly(self, sid: uuid.UUID) -> RiskStatus | None:
        """Get the most recent anomaly flag for a student."""
        stmt = (
            select(StudentStatusHistory.anomaly_flag)
            .where(StudentStatusHistory.sid == sid)
            .order_by(
                desc(StudentStatusHistory.academic_year),
                desc(StudentStatusHistory.semester),
                desc(StudentStatusHistory.week),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        result = result.scalar_one_or_none()

        return RiskStatus(result) if result is not None else None


class SqlAlchemyAdvisorRepository:
    """SQLAlchemy implementation of the AdvisorRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a SQLAlchemy async session."""
        self.session = session

    async def get_by_id(self, advisor_id: uuid.UUID) -> DomainAdvisor:
        """Retrieve an advisor by their unique ID."""
        advisor = await self.find_by_id(advisor_id=advisor_id)
        if advisor is None:
            raise AdvisorNotFoundError(advisor_id=advisor_id)
        return advisor

    async def find_by_id(self, advisor_id: uuid.UUID) -> DomainAdvisor | None:
        """Find an advisor by their unique ID."""
        stmt = select(OrmAdvisor).where(OrmAdvisor.advisor_id == advisor_id)
        result = await self.session.execute(stmt)
        advisor = result.scalar_one_or_none()
        return DataMapper.to_domain_advisor(advisor) if advisor is not None else None

    async def find_by_user_id(self, user_id: uuid.UUID) -> DomainAdvisor | None:
        """Retrieve an advisor by their associated user ID."""
        stmt = select(OrmAdvisor).where(OrmAdvisor.user_id == user_id)
        result = await self.session.execute(stmt)
        advisor = result.scalar_one_or_none()
        return DataMapper.to_domain_advisor(advisor) if advisor else None

    async def get_by_user_id(self, user_id: uuid.UUID) -> DomainAdvisor:
        """Retrieve an advisor by their associated user ID."""
        advisor = await self.find_by_user_id(user_id)
        if advisor is None:
            raise UserIsNotAnAdvisorError(user_id=user_id)
        return advisor

    async def save(self, advisor: DomainAdvisor) -> None:
        stmt = (
            update(OrmAdvisor)
            .where(
                OrmAdvisor.advisor_id == advisor.advisor_id,
            )
            .values(
                name=advisor.name,
                email=advisor.email,
                phone=advisor.phone,
                faculty=advisor.faculty,
                office=advisor.office,
                bio=advisor.bio,
            )
        )
        await self.session.execute(stmt)

    async def upsert_advisor_for_user(
        self,
        user_id: uuid.UUID,
        email: str,
        name: str,
    ) -> None:
        """Link a user to an advisor profile, creating one if necessary."""
        # 1. Check if an advisor with this user_id already exists
        stmt = select(OrmAdvisor).where(OrmAdvisor.user_id == user_id)
        result = await self.session.execute(stmt)
        advisor = result.scalar_one_or_none()

        if advisor:
            advisor.email = email
            advisor.name = name
            return

        # 2. Check if an advisor with this email already exists but is not linked
        stmt = select(OrmAdvisor).where(
            OrmAdvisor.email == email,
            OrmAdvisor.user_id.is_(None),
        )
        result = await self.session.execute(stmt)
        advisor = result.scalar_one_or_none()

        if advisor:
            advisor.user_id = user_id
            advisor.name = name
            return

        # 3. Create new advisor profile
        new_advisor = OrmAdvisor(
            advisor_id=uuid.uuid4(),
            user_id=user_id,
            email=email,
            name=name,
        )
        self.session.add(new_advisor)


class SqlAlchemyIdempotencyRepository:
    """SQLAlchemy implementation of the IdempotencyRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a SQLAlchemy async session."""
        self.session = session

    async def check_key(self, key: uuid.UUID) -> bool:
        """Check if an idempotency key exists."""
        stmt = select(IdempotencyKey).where(IdempotencyKey.key == key)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def record_key(self, key: uuid.UUID) -> None:
        """Record a new idempotency key."""
        entry = IdempotencyKey(key=key)
        self.session.add(entry)
        # await self.session.commit() removed


class SqlAlchemyBadgeRepository:
    """SQLAlchemy implementation of the BadgeRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_advisor_badges(self, advisor_id: uuid.UUID) -> list[str]:
        stmt = select(AdvisorBadge.badge_id).where(
            AdvisorBadge.advisor_id == advisor_id,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def award_badge(self, advisor_id: uuid.UUID, badge_id: str) -> bool:
        stmt = select(AdvisorBadge).where(
            AdvisorBadge.advisor_id == advisor_id,
            AdvisorBadge.badge_id == badge_id,
        )
        existing = (await self.session.execute(stmt)).first()
        if existing:
            return False

        entry = AdvisorBadge(advisor_id=advisor_id, badge_id=badge_id)
        self.session.add(entry)
        return True

    async def get_advisor_stats(self, advisor_id: uuid.UUID) -> dict:
        # Get total points and action count
        # stmt = select(
        #     func.sum(PointLedger.points),
        #     func.count(PointLedger.id),
        # ).where(PointLedger.advisor_id == advisor_id)
        #
        # row = (await self.session.execute(stmt)).first()
        # total_points = row[0] or 0
        # total_actions = row[1] or 0
        #
        # # Get resolves
        # stmt_resolves = (
        #     select(func.count(PointLedger.id))
        #     .where(
        #         PointLedger.advisor_id == advisor_id,
        #         OrmTask.action_type == 'resolve case',
        #     )
        #     .join(OrmTask, PointLedger.task_id == OrmTask.task_id)
        # )
        # total_resolves = (await self.session.execute(stmt_resolves)).scalar() or 0
        #
        # # Fast actions
        # stmt_times = (
        #     select(OrmCase.created_at, PointLedger.earned_at)
        #     .join(OrmTask, OrmCase.case_id == OrmTask.case_id)
        #     .join(PointLedger, OrmTask.task_id == PointLedger.task_id)
        #     .where(OrmCase.assigned_advisor_id == advisor_id)
        #     .where(PointLedger.advisor_id == advisor_id)
        # )
        # time_pairs = (await self.session.execute(stmt_times)).all()
        #
        # total_hours = 0.0
        # fast_action_count = 0
        # valid_pairs = 0
        # for created_at, action_time in time_pairs:
        #     if created_at and action_time:
        #         delta_hours = (
        #             action_time.replace(tzinfo=None) - created_at.replace(tzinfo=None)
        #         ).total_seconds() / 3600.0
        #         if delta_hours < 0:
        #             delta_hours = 0.0
        #         total_hours += delta_hours
        #         valid_pairs += 1
        #         if delta_hours <= 12.0:
        #             fast_action_count += 1
        #
        # avg_response_hours = total_hours / valid_pairs if valid_pairs > 0 else 999.0
        #
        # # Get total cases assigned
        # stmt_cases = select(func.count(OrmCase.case_id)).where(
        #     OrmCase.assigned_advisor_id == advisor_id,
        # )
        # total_cases = (await self.session.execute(stmt_cases)).scalar() or 0
        # recovery_rate = total_resolves / total_cases if total_cases > 0 else 0.0
        #
        return {
            'total_points': 0,
            'fast_action_count': 0,
            'avg_response_hours': 0,
            'total_actions': 0,
            'recovery_rate': 0,
            'total_resolves': 0,
        }


class SqlAlchemyMetadataRepository:
    """SQLAlchemy implementation for metadata retrieval."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with session."""
        self.session = session

    async def get_db_registry(self) -> list[DBDescription]:
        """Get the available database registry."""
        return DB_REGISTRY

    async def list_tables(self, db_id: str) -> list[str]:
        """List tables using SQLAlchemy inspection."""

        def get_tables(connection: Session) -> list[str]:
            # connection here is the synchronous Session object.
            # We need the underlying Connection/Engine for inspection.
            return inspect(connection.get_bind()).get_table_names()

        return await self.session.run_sync(get_tables)

    async def get_table_schema(self, db_id: str, table_name: str) -> str:
        """Get table schema securely and dialect-agnostically."""
        # 1. Validate table_name against the schema to prevent SQL injection
        tables = await self.list_tables(db_id)
        if table_name not in tables:
            raise ValueError(f"Table '{table_name}' does not exist.")

        table_name = quoted_name(table_name, quote=True)

        # 2. Use SQLAlchemy Inspector for dialect-agnostic column retrieval
        def get_columns(connection: Session) -> list[ReflectedColumn]:
            return inspect(connection.get_bind()).get_columns(table_name)

        cols = await self.session.run_sync(get_columns)
        col_lines = [
            f'    - {c["name"]} ({c["type"]}, {"NULLABLE" if c.get("nullable", True) else "NOT NULL"})'
            for c in cols
        ]

        # 3. Safe to interpolate table_name here after validation
        res_sample = await self.session.execute(
            text(f'SELECT * FROM {table_name} LIMIT 3'),
        )
        rows = res_sample.all()
        sample_str = ''
        if rows:
            sample_str = ' | '.join(res_sample.keys()) + '\n' + '-' * 20 + '\n'
            for row in rows:
                sample_str += ' | '.join(map(str, row)) + '\n'

        return (
            f'#### TABLE: {table_name}\n'
            f'- Columns:\n'
            + '\n'.join(col_lines)
            + f'\n- Sample data:\n```\n{sample_str}```'
        )

    async def execute_raw(self, db_id: str, sql: str) -> list[dict[str, Any]]:
        """Execute raw SQL for agent analysis."""
        res = await self.session.execute(text(sql))
        return [dict(zip(res.keys(), row, strict=True)) for row in res.all()]


class SqlAlchemyEmailRepository:
    """SQLAlchemy implementation of the EmailRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a SQLAlchemy async session."""
        self.session = session

    async def add(self, email: DomainInterventionEmail) -> None:
        """Add an intervention email."""
        new_mail = InterventionEmail(
            email_id=email.email_id,
            case_id=email.case_id,
            status=email.status,
            body=email.body,
            subject=email.subject,
            created_at=email.created_at,
            sent_at=email.sent_at,
        )
        self.session.add(new_mail)

    async def save(self, email: DomainInterventionEmail) -> None:
        """Update the content and status of an existing case email."""
        stmt = (
            update(InterventionEmail)
            .where(InterventionEmail.case_id == email.case_id)
            .values(
                status=email.status,
                body=email.body,
                subject=email.subject,
                sent_at=email.sent_at,
            )
        )
        await self.session.execute(stmt)

    async def get_by_case(self, case_id: uuid.UUID) -> DomainInterventionEmail:
        """Find the email associated with a specific case."""
        email = await self.find_by_case(case_id=case_id)
        if email is None:
            raise EmailNotFoundError(case_id=case_id)
        return email

    async def find_by_case(self, case_id: uuid.UUID) -> DomainInterventionEmail | None:
        """Retrieve the email associated with a specific case."""
        stmt = (
            select(InterventionEmail)
            .where(InterventionEmail.case_id == case_id)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        email = result.scalar_one_or_none()
        return DataMapper.to_domain_email(email) if email else None


class SqlAlchemyCaseRepository:
    """SQLAlchemy implementation of the CaseRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a SQLAlchemy async session."""
        self.session = session

    async def add(self, case: DomainCase) -> None:
        """Add a new case."""
        new_case = OrmCase(
            case_id=case.case_id,
            sid=case.sid,
            intervention_status=case.intervention_status,
            created_at=case.created_at,
            assigned_at=case.assigned_at,
            closed_at=case.closed_at,
            version=case.version,
            assigned_advisor_id=case.assigned_advisor_id,
        )
        self.session.add(new_case)

    async def get_active_case(self, sid: uuid.UUID) -> DomainCase | None:
        """Retrieve the active case for a student, if any."""
        stmt = (
            select(OrmCase)
            .where(
                OrmCase.sid == sid,
                OrmCase.intervention_status.in_(
                    [
                        InterventionStatus.NEW,
                        InterventionStatus.ACCEPTED,
                        InterventionStatus.SENT,
                        InterventionStatus.BOOKED,
                        InterventionStatus.SUPPORTING,
                    ],
                ),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        orm_case = result.scalar_one_or_none()
        return DataMapper.to_domain_case(orm_case) if orm_case else None

    async def save(self, case: DomainCase) -> None:
        stmt = (
            update(OrmCase)
            .where(
                OrmCase.case_id == case.case_id,
                OrmCase.version == case.version,
            )
            .values(
                assigned_advisor_id=case.assigned_advisor_id,
                intervention_status=case.intervention_status,
                version=case.version + 1,
            )
        )
        result = await self.session.execute(stmt)

        if result.rowcount == 0:  # type: ignore
            raise ConcurrencyError('Data was modified by another process.')

    async def assign_case(self, case_id: uuid.UUID, advisor_id: uuid.UUID) -> bool:
        """Assign an advisor to a case."""
        stmt = (
            update(OrmCase)
            .where(
                OrmCase.case_id == case_id,
                OrmCase.assigned_advisor_id.is_(None),
            )
            .values(
                assigned_advisor_id=advisor_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0  # type: ignore

    async def get_by_id(self, case_id: uuid.UUID) -> DomainCase:
        """Retrieve a case by its ID."""
        case = await self.find_by_id(case_id=case_id)
        if case is None:
            raise CaseNotFoundError(case_id=case_id)
        return case

    async def find_by_id(self, case_id: uuid.UUID) -> DomainCase | None:
        """Retrieve a case by its ID."""
        stmt = select(OrmCase).where(OrmCase.case_id == case_id)
        result = await self.session.execute(stmt)
        case = result.scalar_one_or_none()
        return DataMapper.to_domain_case(case) if case else None

    async def get_student_cases(self, sid: uuid.UUID) -> list[DomainCase]:
        """Retrieve all cases for a specific student."""
        stmt = (
            select(OrmCase).where(OrmCase.sid == sid).order_by(desc(OrmCase.created_at))
        )
        result = await self.session.execute(stmt)
        return [DataMapper.to_domain_case(row[0]) for row in result.all()]


# class SqlAlchemyTaskRepository:
#     """SQLAlchemy implementation of the TaskRepository."""
#
#     def __init__(self, session: AsyncSession) -> None:
#         """Initialize with a SQLAlchemy async session."""
#         self.session = session
#
#     async def create_task(self, task: DomainTask) -> None:
#         """Create a new task."""
#         orm_task = OrmTask(
#             task_id=task.task_id,
#             case_id=task.case_id,
#             action_type=task.action_type.value,
#             status=task.status.value,
#             points_reward=task.points_reward,
#             created_at=task.created_at,
#         )
#         self.session.add(orm_task)
#
#     async def get_by_id(self, task_id: uuid.UUID) -> DomainTask | None:
#         """Retrieve a task by its ID."""
#         stmt = select(OrmTask).where(OrmTask.task_id == task_id)
#         result = await self.session.execute(stmt)
#         task = result.scalar_one_or_none()
#         return DataMapper.to_domain_task(task) if task else None
#
#     async def get_by_case(self, case_id: uuid.UUID) -> list[DomainTask]:
#         """Retrieve all tasks for a specific case."""
#         stmt = select(OrmTask).where(OrmTask.case_id == case_id)
#         result = await self.session.execute(stmt)
#         return [DataMapper.to_domain_task(t) for t in result.scalars().all()]
#
#     async def update_task(self, task: DomainTask) -> None:
#         """Update an existing task."""
#         stmt = (
#             update(OrmTask)
#             .where(OrmTask.task_id == task.task_id)
#             .values(
#                 status=task.status.value,
#                 points_reward=task.points_reward,
#                 completed_at=task.completed_at,
#                 completed_by_advisor_id=task.completed_by_advisor_id,
#             )
#         )
#         await self.session.execute(stmt)


class SqlAlchemyMetricsRepository:
    """SQLAlchemy implementation of the MetricsRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a SQLAlchemy async session."""
        self.session = session

    async def get_kpi_stats(self) -> dict[str, Any]:
        """Calculate high-level KPI stats."""
        # 1. Retention & Dropout
        total_stmt = select(func.count(Student.sid))
        total_res = await self.session.execute(total_stmt)
        total = total_res.scalar() or 1

        normal_stmt = select(func.count(Student.sid)).where(
            Student.current_risk_status == 'Normal',
        )
        normal_res = await self.session.execute(normal_stmt)
        normal = normal_res.scalar() or 0

        dropout_stmt = select(func.count(Student.sid)).where(
            Student.current_risk_status.like('%Significant Drop%'),
        )
        dropout_res = await self.session.execute(dropout_stmt)
        dropout = dropout_res.scalar() or 0

        retention_rate = (normal / total) * 100
        dropout_rate = (dropout / total) * 100

        # 2. Interventions
        int_stmt = select(func.count(distinct(OrmCase.sid))).where(
            OrmCase.intervention_status != InterventionStatus.NEW
        )
        int_res = await self.session.execute(int_stmt)
        int_count = int_res.scalar() or 0

        # 3. Advisor Engagement
        active_advisors_stmt = select(
            func.count(func.distinct(PointLedger.advisor_id)),
        )
        active_advisors_res = await self.session.execute(active_advisors_stmt)
        active_advisors = active_advisors_res.scalar() or 0

        total_advisors_stmt = select(func.count(OrmAdvisor.advisor_id))
        total_advisors_res = await self.session.execute(total_advisors_stmt)
        total_advisors = total_advisors_res.scalar() or 1

        engagement = (active_advisors / total_advisors) * 100

        return {
            'retention_rate': round(retention_rate, 1),
            'total_interventions': int_count,
            'advisor_engagement': round(float(engagement), 1),
            'dropout_rate': round(dropout_rate, 1),
            'total_students': total,
        }

    async def get_retention_trend(self) -> list[dict[str, Any]]:
        """Retrieve retention trend data over time."""
        stmt = (
            select(
                (
                    literal('W').concat(func.cast(StudentStatusHistory.week, String))
                ).label('month'),
                cast(literal_column('80'), Integer).label('baseline'),
                (
                    func.count(
                        case((StudentStatusHistory.anomaly_flag == 'Normal', 1)),
                    )
                    * 100.0
                    / func.count(StudentStatusHistory.history_id)
                ).label('current'),
            )
            .group_by(
                StudentStatusHistory.academic_year,
                StudentStatusHistory.semester,
                StudentStatusHistory.week,
            )
            .order_by(
                desc(StudentStatusHistory.academic_year),
                desc(StudentStatusHistory.semester),
                desc(StudentStatusHistory.week),
            )
            .limit(12)
        )

        result = await self.session.execute(stmt)
        # Reverse to get chronological order
        return [dict(row) for row in result.mappings().all()][::-1]


class SqlAlchemyJobRepository:
    """SQLAlchemy implementation of the JobRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a SQLAlchemy async session."""
        self.session = session

    async def add(self, job: Job) -> None:
        """Record an background job."""
        orm_job = BackgroundJobTracker(
            job_id=job.job_id,
            status=job.status,
            correlation_id=job.correlation_id,
            correlation_type=job.correlation_type,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.ended_at,
        )
        self.session.add(orm_job)

    async def get_by_id(self, job_id: uuid.UUID) -> Job:
        """Get a job by id."""
        stmt = select(BackgroundJobTracker).where(
            BackgroundJobTracker.job_id == job_id,
        )
        result = await self.session.execute(stmt)
        value = result.scalar_one_or_none()
        if value is None:
            raise JobNotFoundError(job_id=job_id)
        return DataMapper.to_domain_job(value)

    async def find_by_correlation_id(
        self,
        correlation_id: uuid.UUID,
        correlation_type: str,
    ) -> Job | None:
        """Find job by a correlation id."""
        stmt = select(BackgroundJobTracker).where(
            BackgroundJobTracker.correlation_id == correlation_id,
            BackgroundJobTracker.correlation_type == correlation_type,
        )
        result = await self.session.execute(stmt)
        value = result.scalar_one_or_none()
        return DataMapper.to_domain_job(value) if value else None

    async def get_by_correlation_id(
        self,
        correlation_id: uuid.UUID,
        correlation_type: str,
    ) -> Job:
        """Find job by a correlation id."""
        res = await self.find_by_correlation_id(correlation_id, correlation_type)
        if res is None:
            raise JobNotFoundError(correlation_id=correlation_id)
        return res

    async def save(self, job: Job) -> None:
        """Update an existing job."""
        stmt = (
            update(BackgroundJobTracker)
            .where(BackgroundJobTracker.job_id == job.job_id)
            .values(
                status=job.status,
                started_at=job.started_at,
                completed_at=job.ended_at,
            )
        )
        await self.session.execute(stmt)


class SqlAlchemyUserSettingsRepository:
    """SQLAlchemy implementation of the UserSettingsRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a SQLAlchemy async session."""
        self.session = session

    async def get_auto_draft_enabled(self, user_id: uuid.UUID) -> bool:
        """Check if auto-drafting is enabled for a user."""
        stmt = select(UserSettings.auto_draft_enabled).where(
            UserSettings.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        value = result.scalar_one_or_none()

        # Lazy initialization: return True (default) if no setting exists
        return True if value is None else value

    async def update_auto_draft_enabled(
        self,
        user_id: uuid.UUID,
        enabled: bool,
    ) -> None:
        """Update the auto-drafting setting for a user."""
        # Upsert logic
        dialect = self.session.bind.dialect.name if self.session.bind else 'sqlite'
        values = {'user_id': user_id, 'auto_draft_enabled': enabled}

        if dialect == 'postgresql':
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            stmt = (
                pg_insert(UserSettings)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=['user_id'],
                    set_={'auto_draft_enabled': enabled},
                )
            )
        else:
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert

            stmt = (
                sqlite_insert(UserSettings)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=['user_id'],
                    set_={'auto_draft_enabled': enabled},
                )
            )

        await self.session.execute(stmt)

    async def create_user_settings(self, user_id: uuid.UUID) -> None:
        """Create a new default settings for an user."""
        new_settings = UserSettings(
            user_id=user_id,
            auto_draft_enabled=True,
        )

        self.session.add(new_settings)


class SqlAlchemyPointLedgerRepository:
    """SQLAlchemy implementation of the PointLedgerRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a SQLAlchemy async session."""
        self.session = session

    async def get_by_advisor_id(self, advisor_id: uuid.UUID) -> DomainLedger:
        """Retrieve the point ledger for a specific advisor."""
        stmt = (
            select(PointLedger)
            .where(PointLedger.advisor_id == advisor_id)
            .order_by(PointLedger.earned_at.asc())
        )
        result = await self.session.execute(stmt)
        entries = list(result.scalars().all())
        return DataMapper.to_domain_ledger(advisor_id, entries)

    async def save(self, ledger: DomainLedger) -> None:
        """Persist new entries from the ledger."""
        pending = ledger.get_pending_entries()
        for domain_entry in pending:
            orm_entry = DataMapper.to_orm_ledger(domain_entry)
            self.session.add(orm_entry)

        ledger.clear_pending_entries()
