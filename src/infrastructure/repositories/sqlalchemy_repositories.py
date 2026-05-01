"""SQLAlchemy implementations of the repository ports."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    String,
    case,
    desc,
    func,
    inspect,
    literal,
    literal_column,
    quoted_name,
    select,
    text,
    update,
)
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.domain.entities.alert import Alert
from src.domain.value_objects.status import RiskStatus
from src.infrastructure.database.config import DB_REGISTRY
from src.infrastructure.database.mappers import DataMapper
from src.infrastructure.database.models import (
    Activity,
    Advisor,
    AdvisorPointsLedger,
    IdempotencyKey,
    InterventionEmail,
    Student,
    StudentStatusHistory,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.engine.interfaces import ReflectedColumn
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import Session

    from src.domain.entities.advisor import Advisor as DomainAdvisor
    from src.domain.entities.alert import Alert as DomainAlert
    from src.domain.entities.intervention_email import (
        InterventionEmail as DomainInterventionEmail,
    )
    from src.domain.entities.student import Student as DomainStudent
    from src.domain.value_objects.status import InterventionStatus


class SqlAlchemyStudentRepository:
    """SQLAlchemy implementation of the StudentRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a SQLAlchemy async session."""
        self.session = session

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

    async def update_draft_job_id(self, sid: uuid.UUID, job_id: uuid.UUID | None) -> None:
        """Update the draft job ID for a student."""
        stmt = update(Student).where(Student.sid == sid).values(draft_job_id=job_id)
        await self.session.execute(stmt)

    async def batch_update_draft_job_ids(self, updates: Sequence[tuple[uuid.UUID, uuid.UUID]]) -> None:
        """Batch update draft job IDs for multiple students."""
        if not updates:
            return

        # Prepare bulk update data
        update_data = [{'sid': sid, 'draft_job_id': job_id} for job_id, sid in updates]

        # Execute single bulk update
        await self.session.execute(update(Student), update_data)
        # await self.session.commit() removed

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

        # Dynamically choose insert implementation based on dialect
        dialect = self.session.bind.dialect.name if self.session.bind else 'sqlite'
        if dialect == 'postgresql':
            from sqlalchemy.dialects.postgresql import (  # noqa: PLC0415
                insert as pg_insert,
            )

            stmt = pg_insert(Student).values(records).on_conflict_do_nothing()
        else:
            stmt = sqlite_insert(Student).values(records).on_conflict_do_nothing()

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

        # Dynamically choose insert implementation based on dialect
        dialect = self.session.bind.dialect.name if self.session.bind else 'sqlite'
        if dialect == 'postgresql':
            from sqlalchemy.dialects.postgresql import (  # noqa: PLC0415
                insert as pg_insert,
            )

            stmt = pg_insert(Activity).values(records).on_conflict_do_nothing()
        else:
            stmt = sqlite_insert(Activity).values(records).on_conflict_do_nothing()

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
        return [row._asdict() for row in result.all()]

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

    async def get_db_registry(self) -> list[dict[str, Any]]:
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
        if res.returns_rows:
            return [dict(zip(res.keys(), row, strict=True)) for row in res.all()]
        return []


class SqlAlchemyEmailRepository:
    """SQLAlchemy implementation of the EmailRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a SQLAlchemy async session."""
        self.session = session

    async def get_latest_draft(self, sid: uuid.UUID) -> DomainInterventionEmail | None:
        """Retrieve the latest draft email for a student."""
        stmt = (
            select(InterventionEmail)
            .where(
                InterventionEmail.sid == sid,
                InterventionEmail.status == 'draft',
            )
            .order_by(desc(InterventionEmail.created_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        email = result.scalar_one_or_none()
        return DataMapper.to_domain_email(email) if email else None

    async def create_draft(
        self,
        sid: uuid.UUID,
        advisor_id: uuid.UUID | None,
        subject: str,
        body: str,
    ) -> uuid.UUID:
        """Create a new draft email and return its ID."""
        email_id = uuid.uuid4()
        email = InterventionEmail(
            email_id=email_id,
            sid=sid,
            advisor_id=advisor_id,
            subject=subject,
            body=body,
            status='draft',
        )
        self.session.add(email)
        # await self.session.commit() removed
        return email_id

    async def mark_as_sent(self, sid: uuid.UUID, body: str) -> None:
        """Mark the latest draft as sent for a student."""
        stmt = (
            select(InterventionEmail.email_id)
            .where(
                InterventionEmail.sid == sid,
                InterventionEmail.status == 'draft',
            )
            .order_by(desc(InterventionEmail.created_at))
            .limit(1)
        )
        res = await self.session.execute(stmt)
        email_id = res.scalar_one_or_none()

        if email_id:
            stmt = (
                update(InterventionEmail)
                .where(InterventionEmail.email_id == email_id)
                .values(
                    status='sent',
                    sent_at=func.current_timestamp(),
                    body=body,
                )
            )
            await self.session.execute(stmt)
            # await self.session.commit() removed

    async def get_history(self, sid: uuid.UUID) -> list[DomainInterventionEmail]:
        """Retrieve the communication history for a student."""
        stmt = (
            select(InterventionEmail)
            .where(InterventionEmail.sid == sid)
            .order_by(desc(InterventionEmail.created_at))
        )
        result = await self.session.execute(stmt)
        return [DataMapper.to_domain_email(row[0]) for row in result.all()]


class SqlAlchemyAlertRepository:
    """SQLAlchemy implementation of the AlertRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a SQLAlchemy async session."""
        self.session = session

    async def get_active_alerts(
        self,
        status_filter: str | None = None,
    ) -> list[DomainAlert]:
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

        result = await self.session.execute(stmt)
        alerts: list[Alert] = []
        for row in result.all():
            row_tuple = row._tuple()
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
                )
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
                literal_column('80').label('baseline'),
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
        return [row._asdict() for row in result.all()][::-1]
