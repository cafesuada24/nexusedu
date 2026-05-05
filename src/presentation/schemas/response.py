"""Models for the Agent Assistant API response."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EmailDraft(BaseModel):
    """Schema for a personalized email draft."""

    sid: str = Field(..., description='Student identifier.')
    recipient_email: str = Field(..., description='Student email address.')
    subject: str = Field(..., description='Email subject line.')
    body: str = Field(..., description='Personalized email body.')


class QueryResponse(BaseModel):
    """Industry standard response schema for data agents."""

    answer: str = Field(
        ...,
        description='The final natural language response from the agent.',
    )
    tables: list[list[dict[str, Any]]] | None = Field(
        None,
        description='A list of tables, where each table is a list of row objects.',
    )
    visualizations: list[dict[str, Any]] | None = Field(
        None,
        description='A list of Plotly JSON objects for data visualization.',
    )
    session_id: str = Field(..., description='The session or thread identifier.')

    model_config = ConfigDict(
        json_schema_extra={
            'example': {
                'answer': 'Here are the student grades for CS101.',
                'tables': [
                    [{'student_id': 1, 'grade': 85}, {'student_id': 2, 'grade': 92}],
                ],
                'visualizations': [
                    {'data': [], 'layout': {'title': 'Grades for CS101'}},
                ],
                'session_id': 'session_123',
            },
        },
    )


class JobAcceptedResponse(BaseModel):
    """Response returned when a query is accepted for background processing."""

    job_id: str = Field(
        ...,
        description='The unique identifier for the background job.',
    )
    status: str = Field('processing', description='The current status of the job.')


class JobStatusResponse(BaseModel):
    """Response returned when polling for job status."""

    job_id: str = Field(..., description='The unique identifier for the job.')
    status: str = Field(
        ...,
        description='The status of the job (processing, completed, failed).',
    )
    progress: int = Field(0, description='The progress percentage of the job.')
    result: Any | None = Field(
        None,
        description='The result of the query if completed.',
    )
    error: str | None = Field(None, description='The error message if the job failed.')
    created_at: str | None = Field(None, description='Job creation timestamp.')
    started_at: str | None = Field(None, description='Job start timestamp.')
    completed_at: str | None = Field(None, description='Job completion timestamp.')


class AlertStudent(BaseModel):
    """Schema for a student in the Kanban alert dashboard."""

    sid: str = Field(..., description='Student identifier.')
    student_name: str = Field(..., description='Student name.')
    email: str = Field(..., description='Student email.')
    current_risk_status: str = Field(..., description='The type of anomaly detected.')
    intervention_status: str = Field(..., description='The current Kanban state.')
    is_generating: bool = Field(
        False,
        description='Whether a background AI draft generation is running.',
    )
    active_case_id: str | None = Field(
        None, description='The ID of the currently active case.'
    )


class TaskDetail(BaseModel):
    """Schema for a specific task within a case."""

    task_id: str = Field(..., description='Unique task identifier.')
    action_type: str = Field(..., description='The action required (e.g., send email).')
    status: str = Field(..., description='Task status (pending, completed).')
    points_reward: int = Field(..., description='Points awarded upon completion.')
    completed_at: str | None = Field(None, description='When the task was completed.')
    completed_by_advisor_id: str | None = Field(
        None, description='Who completed the task.'
    )


class TaskItem(BaseModel):
    """Schema for a task in the advisor task list."""

    case_id: str = Field(..., description='Case identifier.')
    sid: str = Field(..., description='Student id')
    created_at: str = Field(..., description='When the case was created.')
    assigned_advisor_id: str | None = Field(
        None, description='Advisor assigned to the case.'
    )
    student_name: str | None = Field(None, description='Student name.')
    email: str | None = Field(None, description='Student email.')
    major: str = Field(..., description='Student major.')
    current_risk_status: str = Field(..., description='Risk status.')
    intervention_status: str = Field(..., description='Intervention status.')
    draft_subject: str | None = Field(None, description='Draft email subject.')
    draft_body: str | None = Field(None, description='Draft email body.')
    draft_status: str | None = Field(None, description='Draft email status.')
    assigned_to: str | None = Field(None, description='Name of assigned advisor.')
    suggested_action: str = Field(..., description='Computed action to take.')
    points_reward: int = Field(..., description='Points for completing action.')
    tasks: list[TaskDetail] | None = Field(None, description='Detailed sub-tasks.')


class LeaderboardEntry(BaseModel):
    """Schema for a single entry in the advisor leaderboard."""

    advisor_id: str = Field(..., description='Unique advisor identifier.')
    name: str = Field(..., description='Advisor name.')
    total_points: int = Field(..., description='Total points earned.')
    actions_count: int = Field(..., description='Total actions taken.')
    sent_count: int = Field(..., description='Emails sent.')
    resolved_count: int = Field(..., description='Students resolved.')
