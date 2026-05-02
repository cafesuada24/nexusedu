"""SQLAlchemy ORM models for all domain entities and authentication."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Double,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

if TYPE_CHECKING:
    pass


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class User(SQLAlchemyBaseUserTableUUID, Base):
    """SQLAlchemy model for the User table, integrating with FastAPI-Users."""

    role: Mapped[str] = mapped_column(String, default='viewer')


class Student(Base):
    """Student record from the Student Information System (SIS)."""

    __tablename__ = 'students'

    sid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_name: Mapped[str | None] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String)
    major: Mapped[str] = mapped_column(String, default='Unknown')
    current_risk_status: Mapped[str] = mapped_column(String, default='Normal')
    intervention_status: Mapped[str] = mapped_column(String, default='none')
    last_notified_timestamp: Mapped[float] = mapped_column(Double, default=0)
    last_notified_satisfaction: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    activities: Mapped[list[Activity]] = relationship(
        'Activity', back_populates='student'
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
    timestamp: Mapped[float | None] = mapped_column(Double)
    academic_year: Mapped[int | None] = mapped_column(Integer)
    semester: Mapped[int | None] = mapped_column(Integer)
    week: Mapped[int | None] = mapped_column(Integer)

    # Relationships
    student: Mapped[Student] = relationship('Student', back_populates='activities')


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
        TIMESTAMP,
        server_default=func.current_timestamp(),
    )

    # Relationships
    student: Mapped[Student] = relationship('Student', back_populates='status_history')


class Advisor(Base):
    """Academic advisor profile."""

    __tablename__ = 'advisors'

    advisor_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str | None] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String)


class AdvisorPointsLedger(Base):
    """Ledger recording points earned by advisors for intervention actions."""

    __tablename__ = 'advisor_points_ledger'
    __table_args__ = (
        Index('ix_ledger_advisor_sid_action', 'advisor_id', 'sid', 'action_type'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    advisor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey('advisors.advisor_id'),
    )
    action_type: Mapped[str | None] = mapped_column(String)
    points: Mapped[int | None] = mapped_column(Integer)
    sid: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey('students.sid'))
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP,
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
    advisor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey('advisors.advisor_id'),
    )
    subject: Mapped[str | None] = mapped_column(String)
    body: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String)  # 'draft', 'sent'
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
    )
    sent_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)


class IdempotencyKey(Base):
    """Registry of used idempotency keys to prevent duplicate operations."""

    __tablename__ = 'idempotency_keys'

    key: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
    )


class UserSettings(Base):
    """Configuration settings for a specific user."""

    __tablename__ = 'user_settings'

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey('user.id'),
        primary_key=True,
    )
    auto_draft_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class BackgroundJobTracker(Base):
    """Tracker for ephemeral background jobs tied to a student."""

    __tablename__ = 'background_job_tracker'

    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    sid: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey('students.sid'))
    job_type: Mapped[str] = mapped_column(String, default='email_draft')
    status: Mapped[str] = mapped_column(String, default='running')
