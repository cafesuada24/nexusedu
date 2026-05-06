"""SQLAlchemy ORM models for all domain entities and authentication."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime  # noqa: TC003

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import (
    Boolean,
    DateTime,
    Dialect,
    Double,
    Enum,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    TypeDecorator,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from src.domain.value_objects.status import CaseStatus, RiskStatus


def _all_column_names(constraint: UniqueConstraint | Index, _: Table) -> str:
    return '_'.join(
        [column.name for column in constraint.columns.values()],
    )


_convention = {
    'all_column_names': _all_column_names,
    'ix': 'ix__%(table_name)s__%(all_column_names)s',
    'uq': 'uq__%(table_name)s__%(all_column_names)s',
    'ck': 'ck__%(table_name)s__%(constraint_name)s',
    'fk': 'fk__%(table_name)s__%(all_column_names)s__%(referred_table_name)s',
    'pk': 'pk__%(table_name)s',
}


class UTCDateTime(TypeDecorator[datetime]):
    """Safely coerce SQLite datetimes to be timezone-aware UTC.

    TypeDecorator[datetime.datetime] tells static analyzers that this
    decorator works with Python datetime objects.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(
        self,
        value: datetime | None,
        _: Dialect,
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError('Datetime must be timezone-aware')
        return value.astimezone(UTC)

    def process_result_value(
        self,
        value: datetime | None,
        _: Dialect,
    ) -> datetime | None:
        if value is not None and value.tzinfo is None:
            # SQLite returned a naive datetime, so we "attach" UTC
            return value.replace(tzinfo=UTC)
        return value


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    metadata = MetaData(naming_convention=_convention)


class User(SQLAlchemyBaseUserTableUUID, Base):
    """SQLAlchemy model for the User table, integrating with FastAPI-Users."""

    role: Mapped[str] = mapped_column(String, default='viewer')
    advisor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey('advisors.advisor_id'),
        unique=True,
        nullable=True,
    )

    preferences: Mapped[UserSettings] = relationship(
        'UserSettings',
        back_populates='user',
        uselist=False,
        lazy='selectin',
    )
    # advisor_profile: Mapped[Advisor | None] = relationship(
    #     'Advisor',
    #     back_populates='user',
    #     uselist=False,
    #     lazy='selectin',
    # )


class UserSettings(Base):
    """Configuration settings for a specific user."""

    __tablename__ = 'user_settings'

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('user.id'),
        primary_key=True,
    )
    auto_draft_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped[User] = relationship('User', back_populates='preferences', uselist=False)


class Student(Base):
    """Student record from the Student Information System (SIS)."""

    __tablename__ = 'students'

    sid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_name: Mapped[str | None] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String)
    major: Mapped[str] = mapped_column(String, default='Unknown')
    current_risk_status: Mapped[str] = mapped_column(String, default='Normal')
    intervention_status: Mapped[str] = mapped_column(String, default='none')
    last_notified_timestamp: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_notified_satisfaction: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    activities: Mapped[list[Activity]] = relationship(
        'Activity',
        back_populates='student',
    )
    status_history: Mapped[list[StudentStatusHistory]] = relationship(
        'StudentStatusHistory',
        back_populates='student',
    )


class Activity(Base):
    """Assessment activity record from the Learning Management System (LMS)."""

    __tablename__ = 'activities'

    activity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    sid: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('students.sid'))
    course_id: Mapped[str | None] = mapped_column(String)
    course_name: Mapped[str | None] = mapped_column(String)
    test_type: Mapped[str | None] = mapped_column(String)
    score: Mapped[float | None] = mapped_column(Double)
    timestamp: Mapped[float | None] = mapped_column(UTCDateTime)
    academic_year: Mapped[int | None] = mapped_column(Integer)
    semester: Mapped[int | None] = mapped_column(Integer)
    week: Mapped[int | None] = mapped_column(Integer)

    # Relationships
    student: Mapped[Student] = relationship('Student', back_populates='activities', uselist=False)


class StudentStatusHistory(Base):
    """Historical risk status snapshots for students."""

    __tablename__ = 'student_status_history'

    history_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    sid: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('students.sid'))
    academic_year: Mapped[int | None] = mapped_column(Integer)
    semester: Mapped[int | None] = mapped_column(Integer)
    week: Mapped[int | None] = mapped_column(Integer)
    baseline_avg: Mapped[float | None] = mapped_column(Double)
    baseline_std: Mapped[float | None] = mapped_column(Double)
    current_score_avg: Mapped[float | None] = mapped_column(Double)
    z_score: Mapped[float | None] = mapped_column(Double)
    anomaly_flag: Mapped[str | None] = mapped_column(String)
    status_recorded_at: Mapped[datetime] = mapped_column(
        server_default=func.current_timestamp(),
    )

    # Relationships
    student: Mapped[Student] = relationship('Student', back_populates='status_history', uselist=False)


class Advisor(Base):
    """Academic advisor profile."""

    __tablename__ = 'advisors'

    advisor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str | None] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String)
    title: Mapped[str | None] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String)
    faculty: Mapped[str | None] = mapped_column(String)
    office: Mapped[str | None] = mapped_column(String)
    bio: Mapped[str | None] = mapped_column(Text)

    # Relationships
    user: Mapped[User | None] = relationship('User', uselist=False)


class PointLedger(Base):
    """Ledger recording points earned by users for completed tasks."""

    __tablename__ = 'point_ledger'
    __table_args__ = (Index('ix_ledger_advisor_task', 'advisor_id', 'task_id'),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    advisor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey('advisors.advisor_id'),
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey('tasks.task_id'),
    )
    points: Mapped[int | None] = mapped_column(Integer)
    earned_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        server_default=func.current_timestamp(),
    )


class AdvisorBadge(Base):
    """Registry of achievement badges earned by advisors."""

    __tablename__ = 'advisor_badges'
    __table_args__ = (
        UniqueConstraint('advisor_id', 'badge_id', name='uq_advisor_badge'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    advisor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey('advisors.advisor_id'),
    )
    badge_id: Mapped[str] = mapped_column(String)
    awarded_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        server_default=func.current_timestamp(),
    )


class InterventionEmail(Base):
    """Record of intervention emails drafted or sent to students."""

    __tablename__ = 'intervention_emails'

    email_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    sid: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('students.sid'))
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey('cases.case_id'),
        nullable=True,
    )
    advisor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey('advisors.advisor_id'),
    )
    subject: Mapped[str | None] = mapped_column(String)
    body: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String)  # 'draft', 'sent'
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        server_default=func.now(),
    )
    sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    # Business rule: each intervention case has exactly one email record
    __table_args__ = (
        UniqueConstraint('case_id', name='uq_intervention_emails_case_id'),
    )


class Case(Base):
    """Represents an intervention case for a student."""

    __tablename__ = 'cases'

    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    sid: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('students.sid'))
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus),
        default=CaseStatus.OPEN,
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        server_default=func.now(),
    )
    assigned_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    version: Mapped[int] = mapped_column(Integer, default=0)
    assigned_advisor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey('advisors.advisor_id'),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=func.now(), onupdate=func.now())

    # Relationships
    student: Mapped[Student] = relationship('Student')
    tasks: Mapped[list[Task]] = relationship(
        'Task',
        back_populates='case',
        cascade='all, delete-orphan',
        lazy='selectin',
    )


class Task(Base):
    """Represents a specific task associated with an intervention case."""

    __tablename__ = 'tasks'

    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey('cases.case_id'),
    )
    action_type: Mapped[str] = mapped_column(
        String,
    )  # 'send email', 'student book', 'resolve case'
    status: Mapped[str] = mapped_column(String, default='pending')
    points_reward: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    completed_by_advisor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey('advisors.advisor_id'),
    )

    # Relationships
    case: Mapped[Case] = relationship('Case', back_populates='tasks')


class IdempotencyKey(Base):
    """Registry of used idempotency keys to prevent duplicate operations."""

    __tablename__ = 'idempotency_keys'

    key: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        server_default=func.now(),
    )


class BackgroundJobTracker(Base):
    """Tracker for background jobs with observability and correlation."""

    __tablename__ = 'background_job_tracker'

    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    job_type: Mapped[str] = mapped_column(String, default='email_draft')
    status: Mapped[str] = mapped_column(String, default='running')

    # Observability
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    error_message: Mapped[str | None] = mapped_column(Text)
    progress: Mapped[int] = mapped_column(Integer, default=0)

    # Correlation to connect jobs with other entities (e.g., cases, students)
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    correlation_type: Mapped[str | None] = mapped_column(String)
