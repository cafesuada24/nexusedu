"""Request models for the Agent Assistant API."""

from datetime import datetime
from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    """Schema for an incoming natural language query for the agent."""

    query: str = Field(..., description="The user's query for the agent.")
    thread_id: str | None = Field(
        None,
        pattern='^[a-zA-Z0-9_-]*$',
        description='The session or thread identifier for multi-turn conversations.',
    )
    metadata: dict[str, Any] | None = Field(
        default_factory=dict,
        description='Additional metadata for the request.',
    )

    model_config = ConfigDict(
        json_schema_extra={
            'example': {
                'query': "Show me student grades for 'CS101' in a bar chart.",
                'thread_id': 'session_123',
            },
        },
    )


class SISRecord(BaseModel):
    """Student information system record."""

    student_id: str = Field(
        ...,
        alias='sid',
        pattern='^[a-zA-Z0-9_-]+$',
        description='Unique student identifier.',
    )
    name: str = Field(..., alias='student_name', description='Student full name.')
    email: str = Field(..., description='Student email address.')
    major: str | None = Field('Unknown', description='Student major.')
    current_risk_status: str | None = Field(
        'Normal', description='Current risk status.'
    )
    intervention_status: str | None = Field('none', description='Intervention status.')
    last_notified_timestamp: AwareDatetime | None = Field(
        description='Timestamp of last nudge.',
    )
    last_notified_satisfaction: int | None = Field(
        0,
        description='Satisfaction score of last intervention.',
    )

    model_config = ConfigDict(populate_by_name=True)


class LMSRecord(BaseModel):
    """Learning management system activity record."""

    activity_id: str | None = Field(None, description='Unique activity identifier.')
    student_id: str = Field(..., alias='sid', description='Unique student identifier.')
    course_id: str = Field(..., description='Course identifier.')
    course_name: str = Field(..., description='Full course name.')
    test_type: str = Field(..., description='Type of assessment.')
    score: float = Field(..., description='Numeric score achieved.')
    timestamp: AwareDatetime = Field(..., description='UNIX timestamp of activity.')
    academic_year: int = Field(..., description='Academic year (1-4).')
    semester: int = Field(..., description='Semester (1-2).')
    week: int | None = Field(None, description='Week number (1-16).')

    model_config = ConfigDict(populate_by_name=True)


class CustomDataSource(BaseModel):
    """Flexible schema for custom data sources."""

    source_type: str = Field('custom', pattern='^custom$')
    table_name: str = Field(
        ...,
        pattern='^[a-zA-Z0-9_]+$',
        description='Name of the target table.',
    )
    records: list[dict[str, Any]] = Field(
        ...,
        description='List of arbitrary key-value pairs.',
    )


class CoreDataSource(BaseModel):
    """Wrapper for core SIS or LMS data."""

    source_type: str = Field(..., pattern='^(sis|lms)$')
    records: list[SISRecord] | list[LMSRecord] = Field(
        ...,
        description='List of validated core records.',
    )


class DataIngestionRequest(BaseModel):
    """Request schema for uploading flexible CSV data as JSON."""

    batch_id: str = Field(..., description='Unique identifier for the upload batch.')
    upload_timestamp: str = Field(..., description='ISO timestamp of the upload.')
    data_sources: list[CoreDataSource | CustomDataSource] = Field(
        ...,
        description='List of data sources to ingest.',
    )


class StatusUpdate(BaseModel):
    """Schema for updating a student's intervention status."""

    status: str = Field(..., description='The new Kanban state.')


class SendEmailRequest(BaseModel):
    """Schema for sending a personalized nudge email."""

    body: str = Field(..., description='The final email body to send.')


class TriggerDraftRequest(BaseModel):
    """Schema for triggering a background AI draft generation."""

    booking_link: str | None = Field(None, description='Optional custom booking link.')

