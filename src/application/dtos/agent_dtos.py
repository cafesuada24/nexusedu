"""Data Transfer Objects for agent-related operations."""

from typing import Any

from pydantic import UUID4, BaseModel


class RunAgentTaskCommand(BaseModel):
    """Command to execute an agent task."""

    job_id: UUID4
    query: str
    thread_id: UUID4 | None
    user_dict: dict[str, Any]


class AgentResponseDTO(BaseModel):
    """DTO for the agent's response."""

    answer: str
    tables: list[list[dict[str, Any]]] | None
    session_id: UUID4
