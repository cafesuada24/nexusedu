"""SQLAlchemy ORM models for all domain entities and authentication."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID
from sqlalchemy import (
    Boolean,
    DateTime,
    Dialect,
    Double,
    Enum,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
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

from src.domain.value_objects.status import (
    EmailStatus,
    InterventionStatus,
    JobStatus,
    MeetingMethod,
    OutboxStatus,
    RiskStatus,
)


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
    """Safely coerce datetimes to be timezone-aware UTC for database storage.

    Ensures that naive datetimes are rejected on write and tagged as UTC
    on read, maintaining consistency across the application.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(
        self,
        value: datetime | None,
        _: Dialect,
    ) -> datetime | None:
        """Logic for sending data TO the database.

        Ensures we only save timezone-aware objects converted to UTC.
        """
        if value is None:
            return None

        if not isinstance(value, datetime):
            raise TypeError(f'Expected datetime, received {type(value)}')

        if value.tzinfo is None:
            raise ValueError(
                f'UTCDateTime requires timezone-aware datetimes. Received naive: {value}',
            )

        return value.astimezone(UTC)

    def process_result_value(
        self,
        value: datetime | None,
        _: Dialect,
    ) -> datetime | None:
        """Logic for receiving data FROM the database.

        Ensures the application always receives a UTC-aware datetime.
        """
        if value is None:
            return None

        # Some DB drivers return naive datetimes.
        # replace(tzinfo=UTC) 'tags' it without shifting the hours.
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)

        # If the driver is already TZ-aware, ensure it's converted to UTC
        return value.astimezone(UTC)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    metadata = MetaData(naming_convention=_convention)


class User(SQLAlchemyBaseUserTableUUID, Base):
    """SQLAlchemy model for the User table, integrating with FastAPI-Users."""

    role: Mapped[str] = mapped_column(String, default='viewer', nullable=False)

    preferences: Mapped[UserSettings] = relationship(
        'UserSettings',
        back_populates='user',
        uselist=False,
        lazy='selectin',
        cascade='all, delete-orphan',
    )


class UserSettings(Base):
    """Configuration settings for a specific user."""

    __tablename__ = 'user_settings'

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('user.id', ondelete='CASCADE'),
        primary_key=True,
    )
    auto_draft_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    user: Mapped[User] = relationship(
        'User',
        back_populates='preferences',
        uselist=False,
    )


class Student(Base):
    """Student record from the Student Information System (SIS)."""

    __tablename__ = 'students'

    sid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    email: Mapped[str] = mapped_column(
        String,
        nullable=False,
        unique=True,
        index=True,
    )
    major: Mapped[str] = mapped_column(String, default='Unknown')
    current_risk_status: Mapped[RiskStatus] = mapped_column(
        Enum(RiskStatus),
        default=RiskStatus.NORMAL,
        nullable=False,
        index=True,
    )
    last_notified_timestamp: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_notified_satisfaction: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    activities: Mapped[list[Activity]] = relationship(
        'Activity',
        back_populates='student',
        cascade='all, delete-orphan',
    )
    status_history: Mapped[list[StudentStatusHistory]] = relationship(
        'StudentStatusHistory',
        back_populates='student',
        cascade='all, delete-orphan',
    )


class Activity(Base):
    """Assessment activity record from the Learning Management System (LMS)."""

    __tablename__ = 'activities'

    activity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    sid: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey('students.sid', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    course_id: Mapped[str | None] = mapped_column(String)
    course_name: Mapped[str | None] = mapped_column(String)
    test_type: Mapped[str | None] = mapped_column(String)
    score: Mapped[float | None] = mapped_column(Double, index=True)
    timestamp: Mapped[datetime | None] = mapped_column(UTCDateTime, index=True)
    academic_year: Mapped[int | None] = mapped_column(Integer)
    semester: Mapped[int | None] = mapped_column(Integer)
    week: Mapped[int | None] = mapped_column(Integer)

    # Relationships
    student: Mapped[Student] = relationship(
        'Student',
        back_populates='activities',
        uselist=False,
    )


class StudentStatusHistory(Base):
    """Historical risk status snapshots for students."""

    __tablename__ = 'student_status_history'

    history_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    sid: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey('students.sid', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    academic_year: Mapped[int | None] = mapped_column(Integer)
    semester: Mapped[int | None] = mapped_column(Integer)
    week: Mapped[int | None] = mapped_column(Integer)
    baseline_avg: Mapped[float | None] = mapped_column(Double)
    baseline_std: Mapped[float | None] = mapped_column(Double)
    current_score_avg: Mapped[float | None] = mapped_column(Double)
    z_score: Mapped[float | None] = mapped_column(Double)
    anomaly_flag: Mapped[str | None] = mapped_column(String, index=True)
    status_recorded_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        index=True,
    )

    # Relationships
    student: Mapped[Student] = relationship(
        'Student',
        back_populates='status_history',
        uselist=False,
    )


class Advisor(Base):
    """Academic advisor profile."""

    __tablename__ = 'advisors'

    advisor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey('user.id'),
        unique=True,
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    email: Mapped[str] = mapped_column(
        String,
        nullable=False,
        unique=True,
        index=True,
    )
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
    __table_args__ = (Index('ix_ledger_advisor_case', 'advisor_id', 'case_id'),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    advisor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey('advisors.advisor_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey('cases.case_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(String, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    earned_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        server_default=func.now(),
        index=True,
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
        ForeignKey('advisors.advisor_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    badge_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    awarded_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        server_default=func.now(),
        index=True,
    )


class InterventionEmail(Base):
    """Record of intervention emails drafted or sent to students."""

    __tablename__ = 'intervention_emails'

    email_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey('cases.case_id', ondelete='CASCADE'),
        nullable=False,
    )
    subject: Mapped[str | None] = mapped_column(String)
    body: Mapped[str | None] = mapped_column(Text)
    status: Mapped[EmailStatus] = mapped_column(
        Enum(EmailStatus),
        default=EmailStatus.UNAVAILABLE,
        nullable=False,
        index=True,
    )  # 'draft', 'sent'
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        server_default=func.now(),
        index=True,
    )
    sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    version: Mapped[int] = mapped_column(Integer, default=0)

    # Business rule: each intervention case has exactly one email record
    __table_args__ = (
        UniqueConstraint('case_id', name='uq_intervention_emails_case_id'),
    )


class Appointment(Base):
    """Record of student-advisor appointments."""

    __tablename__ = 'appointments'

    appointment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey('cases.case_id', ondelete='CASCADE'),
        nullable=False,
    )
    appointment_time: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    meeting_method: Mapped[MeetingMethod] = mapped_column(
        Enum(MeetingMethod),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        server_default=func.now(),
        index=True,
    )

    # Business rule: each intervention case has exactly one appointment record
    __table_args__ = (
        UniqueConstraint('case_id', name='uq_appointments_case_id'),
    )


class Case(Base):
    """Represents an intervention case for a student."""

    __tablename__ = 'cases'

    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    sid: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey('students.sid', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    intervention_status: Mapped[InterventionStatus] = mapped_column(
        Enum(InterventionStatus),
        default=InterventionStatus.NEW,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        server_default=func.now(),
        index=True,
    )
    assigned_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    version: Mapped[int] = mapped_column(Integer, default=0)
    assigned_advisor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey('advisors.advisor_id', ondelete='SET NULL'),
        nullable=True,
        default=None,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=func.now(),
        onupdate=func.now(),
        index=True,
    )

    # Relationships
    student: Mapped[Student] = relationship('Student')
    # tasks: Mapped[list[Task]] = relationship(
    #     'Task',
    #     back_populates='case',
    #     cascade='all, delete-orphan',
    #     lazy='selectin',
    # )


# class Task(Base):
#     """Represents a specific task associated with an intervention case."""
#
#     __tablename__ = 'tasks'
#
#     task_id: Mapped[uuid.UUID] = mapped_column(
#         Uuid,
#         primary_key=True,
#         default=uuid.uuid4,
#     )
#     case_id: Mapped[uuid.UUID] = mapped_column(
#         Uuid,
#         ForeignKey('cases.case_id'),
#     )
#     name: Mapped[str] = mapped_column(String)
#     status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.BLOCKED)
#     points_reward: Mapped[int] = mapped_column(Integer, default=0)
#     created_at: Mapped[datetime] = mapped_column(
#         UTCDateTime,
#         server_default=func.now(),
#     )
#     completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
#     # Relationships
#     case: Mapped[Case] = relationship('Case', back_populates='tasks')


class IdempotencyKey(Base):
    """Registry of used idempotency keys to prevent duplicate operations."""

    __tablename__ = 'idempotency_keys'

    key: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        server_default=func.now(),
        index=True,
    )


class BackgroundJobTracker(Base):
    """Tracker for background jobs with observability and correlation."""

    __tablename__ = 'background_job_tracker'

    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus),
        default=JobStatus.PENDING,
        index=True,
    )
    correlation_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    correlation_type: Mapped[str] = mapped_column(String)

    # Observability
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        server_default=func.now(),
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    # Correlation to connect jobs with other entities (e.g., cases, students)


class OutboxEvent(Base):
    """Reliable storage for background tasks to ensure atomic consistency."""

    __tablename__ = 'outbox_events'

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    task_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    payload: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    status: Mapped[OutboxStatus] = mapped_column(
        Enum(OutboxStatus),
        default=OutboxStatus.PENDING,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime,
        nullable=True,
        index=True,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
