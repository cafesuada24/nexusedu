"""Request models for the Agent Assistant API."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    """Schema for an incoming natural language query for the agent."""

    query: str = Field(..., description="The user's query for the agent.")
    thread_id: str | None = Field(None, description="The session or thread identifier for multi-turn conversations.")
    metadata: dict[str, Any] | None = Field(default_factory=dict, description="Additional metadata for the request.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "Show me student grades for 'CS101' in a bar chart.",
                "thread_id": "session_123",
            },
        },
    )
