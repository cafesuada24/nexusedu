"""SQLAlchemy implementations of the repository ports."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Integer,
    String,
    case,
    cast,
    desc,
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

from src.core.config import config
from src.domain.value_objects.status import CaseStatus, EmailStatus, RiskStatus
from src.infrastructure.database.config import DB_REGISTRY
from src.infrastructure.database.mappers import DataMapper
from src.infrastructure.database.models import (
    Activity,
    Advisor,
    AdvisorPointsLedger,
    BackgroundJobTracker,
    IdempotencyKey,
    InterventionEmail,
    Student,
    StudentStatusHistory,
    UserSettings,
)
from src.infrastructure.database.models import Case as OrmCase

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.engine.interfaces import ReflectedColumn
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import Session

    from src.domain.entities.advisor import Advisor as DomainAdvisor
    from src.domain.entities.alert import Alert
    from src.domain.entities.alert import Alert as DomainAlert
    from src.domain.entities.case import Case as DomainCase
    from src.domain.entities.intervention_email import (
        InterventionEmail as DomainInterventionEmail,
    )
    from src.domain.entities.student import Student as DomainStudent
    from src.domain.repositories.metadata_repository import DBDescription
    from src.domain.value_objects.status import InterventionStatus


class SqlAlchemyStudentRepository:
    """SQLAlchemy implementation of the StudentRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a SQLAlchemy async session."""
        self.session = session
        self.chunk_size = config.db_ingest_chunk_size

    async def get_by_id(self, sid: uuid.UUID) -> DomainStudent | None:
        """Retrieve a student by their unique ID."""
        stmt = select(Student).where(Student.sid == sid)
        result = await self.session.execute(stmt)
        student = result.scalar_one_or_none()
        return DataMapper.to_domain_student(student) if student else None

    async def get_pii(self, sid: uuid.UUID) -> dict[str, Any] | None:
        """Retrieve student PII (name and email)."""
        stmt = select(Student.student_name, Student.email).where(Student.sid == sid)
        result = await self.session.execute(stmt)
        row = result.first()
        return {'student_name': row.student_name, 'email': row.email} if row else None

    async def update_intervention_status(
        self,
        sid: uuid.UUID,
        status: InterventionStatus,
    ) -> None:
        """Update the intervention status for a student."""
        stmt = (
            update(Student)
            .where(Student.sid == sid)
            .values(intervention_status=status.value)
        )
        await self.session.execute(stmt)

    async def update_last_notified(self, sid: uuid.UUID) -> None:
        """Update the last notified timestamp for a student."""
        stmt = (
            update(Student)
            .where(Student.sid == sid)
            .values(last_notified_timestamp=time.time())
        )
        await self.session.execute(stmt)

    async def get_latest_status_timestamp(self, sid: uuid.UUID) -> datetime | None:
        """Retrieve the latest status recording timestamp for a student."""
        stmt = (
            select(StudentStatusHistory.status_recorded_at)
            .where(StudentStatusHistory.sid == sid)
            .order_by(desc(StudentStatusHistory.status_recorded_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

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
        return [row._asdict() for row in result.all()]

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

    async def update_risk_status(
        self,
        sid: uuid.UUID,
        risk_status: RiskStatus,
        intervention_status: InterventionStatus | None = None,
    ) -> None:
        """Update the risk and optionally intervention status for a student."""
        values = {'current_risk_status': risk_status.value}
        if intervention_status:
            values['intervention_status'] = intervention_status.value

        stmt = update(Student).where(Student.sid == sid).values(values)
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
        return [row._asdict() for row in result.all()]


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
        return [row._asdict() for row in result.all()]

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

    async def get_by_id(self, advisor_id: uuid.UUID) -> DomainAdvisor | None:
        """Retrieve an advisor by their unique ID."""
        stmt = select(Advisor).where(Advisor.advisor_id == advisor_id)
        result = await self.session.execute(stmt)
        advisor = result.scalar_one_or_none()
        return DataMapper.to_domain_advisor(advisor) if advisor else None

    async def get_engagement_metrics(self) -> list[dict[str, Any]]:
        """Retrieve aggregated engagement metrics by major."""
        stmt = (
            select(
                Student.major.label('faculty'),
                func.count(
                    case(
                        (
                            Student.intervention_status.in_(
                                ['sent', 'booked', 'supporting', 'resolved'],
                            ),
                            1,
                        ),
                    ),
                ).label('sent'),
                func.count(
                    case((Student.intervention_status == 'notified', 1)),
                ).label('drafted'),
            )
            .group_by(Student.major)
            .order_by(desc('sent'))
        )

        result = await self.session.execute(stmt)
        return [row._asdict() for row in result.all()]

    async def get_leaderboard(self, time_window: str) -> list[dict[str, Any]]:
        """Retrieve the advisor leaderboard for a specific time window."""
        interval_map = {
            'weekly': timedelta(days=7),
            'monthly': timedelta(days=30),
            'semester': timedelta(days=120),
        }

        stmt = select(
            AdvisorPointsLedger.advisor_id,
            func.coalesce(
                Advisor.name,
                AdvisorPointsLedger.advisor_id,
            ).label('name'),
            func.sum(AdvisorPointsLedger.points).label('total_points'),
            func.count(AdvisorPointsLedger.id).label('actions_count'),
            func.count(
                case((AdvisorPointsLedger.action_type == 'email_sent', 1)),
            ).label('sent_count'),
            func.count(
                case((AdvisorPointsLedger.action_type == 'student_resolved', 1)),
            ).label('resolved_count'),
        ).outerjoin(Advisor, AdvisorPointsLedger.advisor_id == Advisor.advisor_id)

        if time_window != 'all_time' and time_window in interval_map:
            cutoff = datetime.now() - interval_map[time_window]
            stmt = stmt.where(AdvisorPointsLedger.timestamp >= cutoff)

        stmt = stmt.group_by(
            AdvisorPointsLedger.advisor_id,
            Advisor.name,
        ).order_by(desc('total_points'))

        result = await self.session.execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    async def record_points(
        self,
        advisor_id: uuid.UUID,
        sid: uuid.UUID,
        action_type: str,
        points: int,
    ) -> None:
        """Record gamification points for an advisor action."""
        entry = AdvisorPointsLedger(
            advisor_id=advisor_id,
            sid=sid,
            action_type=action_type,
            points=points,
        )
        self.session.add(entry)
        # await self.session.commit() removed

    async def has_existing_action(
        self, advisor_id: uuid.UUID, sid: uuid.UUID, action_type: str
    ) -> bool:
        """Check if an action has already been recorded for this advisor/student combination."""
        stmt = select(AdvisorPointsLedger).where(
            AdvisorPointsLedger.advisor_id == advisor_id,
            AdvisorPointsLedger.sid == sid,
            AdvisorPointsLedger.action_type == action_type,
        )
        result = await self.session.execute(stmt)
        return result.first() is not None


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

    async def create_placeholder(
        self,
        case_id: uuid.UUID,
        sid: uuid.UUID,
        advisor_id: uuid.UUID | None,
    ) -> uuid.UUID:
        """Create a placeholder email with 'generating' status."""
        email_id = uuid.uuid4()
        email = InterventionEmail(
            email_id=email_id,
            sid=sid,
            case_id=case_id,
            advisor_id=advisor_id,
            status='generating',
        )
        self.session.add(email)
        return email_id

    async def update_content(
        self,
        case_id: uuid.UUID,
        subject: str,
        body: str,
        status: EmailStatus,
    ) -> None:
        """Update the content and status of an existing case email."""
        stmt = (
            update(InterventionEmail)
            .where(InterventionEmail.case_id == case_id)
            .values(subject=subject, body=body, status=status.value)
        )
        await self.session.execute(stmt)

    async def get_by_case(self, case_id: uuid.UUID) -> DomainInterventionEmail | None:
        """Retrieve the email associated with a specific case."""
        stmt = (
            select(InterventionEmail)
            .where(InterventionEmail.case_id == case_id)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        email = result.scalar_one_or_none()
        return DataMapper.to_domain_email(email) if email else None

    async def mark_as_sent(self, case_id: uuid.UUID, body: str) -> None:
        """Mark the case email as sent."""
        stmt = (
            update(InterventionEmail)
            .where(InterventionEmail.case_id == case_id)
            .values(
                body=body,
                status=EmailStatus.SENT.value,
                sent_at=func.current_timestamp(),
            )
        )
        await self.session.execute(stmt)

    async def get_history(self, sid: uuid.UUID) -> list[DomainInterventionEmail]:
        """Retrieve the communication history for a student."""
        stmt = (
            select(InterventionEmail)
            .where(InterventionEmail.sid == sid)
            .order_by(desc(InterventionEmail.created_at))
        )
        result = await self.session.execute(stmt)
        return [DataMapper.to_domain_email(row[0]) for row in result.all()]


class SqlAlchemyCaseRepository:
    """SQLAlchemy implementation of the CaseRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a SQLAlchemy async session."""
        self.session = session

    async def create_case(self, case: DomainCase) -> None:
        """Create a new case."""
        orm_case = OrmCase(
            case_id=case.case_id,
            sid=case.sid,
            status=case.status.value,
            created_at=case.created_at,
        )
        self.session.add(orm_case)

    async def get_active_case(self, sid: uuid.UUID) -> DomainCase | None:
        """Retrieve the active case for a student, if any."""
        stmt = (
            select(OrmCase).where(OrmCase.sid == sid, OrmCase.status == 'open').limit(1)
        )
        result = await self.session.execute(stmt)
        orm_case = result.scalar_one_or_none()
        return DataMapper.to_domain_case(orm_case) if orm_case else None

    async def assign_case(self, case_id: uuid.UUID, advisor_id: uuid.UUID) -> bool:
        """Assign an advisor to a case."""
        stmt = update(OrmCase).where(
            OrmCase.case_id == case_id,
            OrmCase.assigned_advisor_id.is_(None)
        ).values(
            assigned_advisor_id=advisor_id
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def update_case_status(self, case_id: uuid.UUID, status: CaseStatus) -> None:
        """Update the status of a case."""
        stmt = (
            update(OrmCase)
            .where(OrmCase.case_id == case_id)
            .values(status=status.value)
        )
        if status in (CaseStatus.RESOLVED, CaseStatus.CLOSED):
            stmt = stmt.values(resolved_at=func.current_timestamp())
        await self.session.execute(stmt)

    async def get_by_id(self, case_id: uuid.UUID) -> DomainCase | None:
        """Retrieve a case by its ID."""
        stmt = select(OrmCase).where(OrmCase.case_id == case_id)
        result = await self.session.execute(stmt)
        orm_case = result.scalar_one_or_none()
        return DataMapper.to_domain_case(orm_case) if orm_case else None

    async def get_student_cases(self, sid: uuid.UUID) -> list[DomainCase]:
        """Retrieve all cases for a specific student."""
        stmt = (
            select(OrmCase).where(OrmCase.sid == sid).order_by(desc(OrmCase.created_at))
        )
        result = await self.session.execute(stmt)
        return [DataMapper.to_domain_case(row[0]) for row in result.all()]

    async def get_task_list(
        self,
        advisor_id: uuid.UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list['TaskItemRecord'], int]:
        """Retrieve task list table for advisors with pagination."""
        from src.infrastructure.database.models import Case as OrmCase
        from src.infrastructure.database.models import Student as OrmStudent
        from src.infrastructure.database.models import InterventionEmail as OrmEmail
        from src.infrastructure.database.models import Advisor as OrmAdvisor
        from src.domain.entities.case import TaskItemRecord
        from src.domain.value_objects.status import RiskStatus, InterventionStatus

        stmt = (
            select(
                OrmCase.case_id,
                OrmCase.created_at,
                OrmCase.assigned_advisor_id,
                OrmStudent.student_name,
                OrmStudent.email,
                OrmStudent.major,
                OrmStudent.current_risk_status,
                OrmStudent.intervention_status,
                OrmEmail.subject.label('draft_subject'),
                OrmEmail.body.label('draft_body'),
                OrmEmail.status.label('draft_status'),
                OrmAdvisor.name.label('assigned_to')
            )
            .join(OrmStudent, OrmCase.sid == OrmStudent.sid)
            .outerjoin(OrmEmail, OrmCase.case_id == OrmEmail.case_id)
            .outerjoin(OrmAdvisor, OrmCase.assigned_advisor_id == OrmAdvisor.advisor_id)
            .where(OrmCase.status == 'open')
            .order_by(desc(OrmCase.created_at))
        )
        if advisor_id is not None:
            stmt = stmt.where(
                or_(
                    OrmCase.assigned_advisor_id == advisor_id,
                    OrmCase.assigned_advisor_id.is_(None),
                )
            )

        # Count total items before applying limit/offset
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.session.execute(count_stmt)
        total_count = count_result.scalar() or 0

        # Apply limit and offset
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        
        tasks = []
        for row in result.mappings().all():
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

            tasks.append(TaskItemRecord(
                case_id=row['case_id'],
                created_at=row['created_at'],
                assigned_advisor_id=row['assigned_advisor_id'],
                student_name=row['student_name'],
                email=row['email'],
                major=row['major'] or 'Unknown',
                current_risk_status=risk_status,
                intervention_status=intervention_status,
                draft_subject=row['draft_subject'],
                draft_body=row['draft_body'],
                draft_status=row['draft_status'],
                assigned_to=row['assigned_to'],
                suggested_action='N/A',  # Will be populated by the application layer
            ))
        return tasks


class SqlAlchemyAlertRepository:
    """SQLAlchemy implementation of the AlertRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a SQLAlchemy async session."""
        self.session = session

    async def get_active_alerts(
        self,
        status_filter: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[DomainAlert], int]:
        """Retrieve students with active alerts for the Kanban board."""
        # Subquery to get latest draft
        subq = (
            select(
                InterventionEmail.sid,
                InterventionEmail.subject,
                InterventionEmail.body,
                func.row_number()
                .over(
                    partition_by=InterventionEmail.sid,
                    order_by=desc(InterventionEmail.created_at),
                )
                .label('rn'),
            )
            .where(InterventionEmail.status == 'draft')
            .subquery()
        )

        latest_draft = select(subq).where(subq.c.rn == 1).subquery()

        stmt = (
            select(Student, latest_draft.c.subject, latest_draft.c.body)
            .outerjoin(latest_draft, Student.sid == latest_draft.c.sid)
            .where(Student.intervention_status != 'none')
        )

        if status_filter:
            stmt = stmt.where(Student.intervention_status == status_filter)

        # Count total items
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.session.execute(count_stmt)
        total_count = count_result.scalar() or 0

        # Apply paging
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        alerts: list[DomainAlert] = []
        for row in result.all():
            row_tuple = tuple(row)
            orm_student = row_tuple[0]
            draft_subject = row_tuple[1]
            draft_body = row_tuple[2]
            alerts.append(
                DataMapper.to_domain_alert(
                    orm_student,
                    {
                        'draft_subject': draft_subject,
                        'draft_body': draft_body,
                    },
                ),
            )
        return alerts


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
        int_stmt = select(func.count(Student.sid)).where(
            Student.intervention_status != 'none',
        )
        int_res = await self.session.execute(int_stmt)
        int_count = int_res.scalar() or 0

        # 3. Advisor Engagement
        active_advisors_stmt = select(
            func.count(func.distinct(AdvisorPointsLedger.advisor_id)),
        )
        active_advisors_res = await self.session.execute(active_advisors_stmt)
        active_advisors = active_advisors_res.scalar() or 0

        total_advisors_stmt = select(func.count(Advisor.advisor_id))
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

    async def create_job(
        self,
        job_id: uuid.UUID,
        job_type: str,
        correlation_id: uuid.UUID | None = None,
        correlation_type: str | None = None,
    ) -> None:
        """Record a new background job with optional correlation."""
        entry = BackgroundJobTracker(
            job_id=job_id,
            job_type=job_type,
            correlation_id=correlation_id,
            correlation_type=correlation_type,
            status='running',
        )
        self.session.add(entry)

    async def update_job_progress(
        self,
        job_id: uuid.UUID,
        progress: int,
        status_message: str | None = None,
    ) -> None:
        """Update the progress and status message of a job."""
        stmt = (
            update(BackgroundJobTracker)
            .where(BackgroundJobTracker.job_id == job_id)
            .values(progress=progress, error_message=status_message)
        )
        await self.session.execute(stmt)

    async def start_job(self, job_id: uuid.UUID) -> None:
        """Mark a job as started."""
        stmt = (
            update(BackgroundJobTracker)
            .where(BackgroundJobTracker.job_id == job_id)
            .values(started_at=func.current_timestamp(), status='processing')
        )
        await self.session.execute(stmt)

    async def complete_job(self, job_id: uuid.UUID) -> None:
        """Mark a background job as completed."""
        stmt = (
            update(BackgroundJobTracker)
            .where(BackgroundJobTracker.job_id == job_id)
            .values(
                completed_at=func.current_timestamp(),
                status='completed',
                progress=100,
            )
        )
        await self.session.execute(stmt)

    async def fail_job(self, job_id: uuid.UUID, error_message: str) -> None:
        """Mark a background job as failed."""
        stmt = (
            update(BackgroundJobTracker)
            .where(BackgroundJobTracker.job_id == job_id)
            .values(
                completed_at=func.current_timestamp(),
                status='failed',
                error_message=error_message,
            )
        )
        await self.session.execute(stmt)

    async def get_active_job(
        self,
        correlation_id: uuid.UUID,
        correlation_type: str,
        job_type: str,
    ) -> uuid.UUID | None:
        """Retrieve the active job ID for a specific correlation context."""
        stmt = select(BackgroundJobTracker.job_id).where(
            BackgroundJobTracker.correlation_id == correlation_id,
            BackgroundJobTracker.correlation_type == correlation_type,
            BackgroundJobTracker.job_type == job_type,
            BackgroundJobTracker.status.in_(['running', 'processing']),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def batch_create_jobs(
        self,
        jobs: Sequence[tuple[uuid.UUID, str, uuid.UUID | None, str | None]],
    ) -> None:
        """Batch record multiple background jobs."""
        if not jobs:
            return

        entries = [
            BackgroundJobTracker(
                job_id=job_id,
                job_type=job_type,
                correlation_id=corr_id,
                correlation_type=corr_type,
                status='running',
            )
            for job_id, job_type, corr_id, corr_type in jobs
        ]
        self.session.add_all(entries)

    async def get_job(self, job_id: uuid.UUID) -> dict[str, Any] | None:
        """Retrieve job details for observability."""
        stmt = select(BackgroundJobTracker).where(BackgroundJobTracker.job_id == job_id)
        result = await self.session.execute(stmt)
        orm_job = result.scalar_one_or_none()

        if not orm_job:
            return None

        return {
            'job_id': str(orm_job.job_id),
            'job_type': orm_job.job_type,
            'status': orm_job.status,
            'progress': orm_job.progress,
            'error_message': orm_job.error_message,
            'created_at': orm_job.created_at.isoformat()
            if orm_job.created_at
            else None,
            'started_at': orm_job.started_at.isoformat()
            if orm_job.started_at
            else None,
            'completed_at': orm_job.completed_at.isoformat()
            if orm_job.completed_at
            else None,
            'correlation_id': str(orm_job.correlation_id)
            if orm_job.correlation_id
            else None,
            'correlation_type': orm_job.correlation_type,
        }


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
