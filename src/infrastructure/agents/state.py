"""Global state definitions for the agent assistant."""

from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph import add_messages

from src.infrastructure.agents.schemas import DiscoveryRequest, PlannerTask

# Type Aliases for clarity
type MessageList = list[dict[str, str]]
type ResultList = list[dict[str, Any]]

# Context Limits
MAX_MESSAGES = 20
MAX_RESULTS = 10
MAX_DISCOVERY_DEPTH = 2


class SQLTask(TypedDict):
    """Internal state for a parallel SQL worker task."""

    db_id: str
    dialect: str
    query_intent: str
    schema_hint: str


class RoutingMetadata(TypedDict, total=False):
    """Structured routing metadata for the agent."""

    path: Literal[
        'SQL_EXECUTION',
        'DIRECT_ANSWER',
        'DISCOVERY_REQUIRED',
        'EXTERNAL_TOOL',
    ]
    direct_response_draft: str | None
    discovery_requests: list[DiscoveryRequest]
    next_action_after_sql: Literal['RESPOND', 'EMAIL_DRAFT']


def last_value_reducer(x: object, y: object) -> object:
    """Keep the last non-None value."""
    return y if y is not None else x


def results_reducer(current: ResultList, next_val: ResultList | None) -> ResultList:
    """Merge results from workers, or clear if None is received."""
    if next_val is None:
        return []
    return (current or []) + next_val


class AgentState(TypedDict):
    """Global state for the agent workflow."""

    messages: Annotated[MessageList, add_messages]
    worker_states: dict[str, Any]
    tasks: list[SQLTask]
    results: Annotated[ResultList, results_reducer]
    final_data: Annotated[ResultList | None, last_value_reducer]  # type: ignore[reportInvalidTypeForm]
    retry_count: int
    next_step: str
    discovery_context: str | None
    discovery_depth: int
    routing_metadata: RoutingMetadata
