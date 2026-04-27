"""Models for the Agent Assistant API response."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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
    result: Any | None = Field(
        None,
        description='The result of the query if completed.',
    )
    error: str | None = Field(None, description='The error message if the job failed.')
