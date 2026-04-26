"""Global state definitions for the agent assistant."""

from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import add_messages

# Type Aliases for clarity
type MessageList = list[BaseMessage]
type ResultList = list[dict[str, Any]]

class SQLTask(TypedDict):
    """Internal state for a parallel SQL worker task."""
    db_id: str
    dialect: str
    query_intent: str
    schema_hint: str
    # message: str

def last_value_reducer(x: object, y: object) -> object:
    """Keep the last non-None value."""
    if y is None:
        return x
    return y

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
    final_data: Annotated[ResultList | None, last_value_reducer]
    retry_count: int
    next_step: str
    discovery_context: str | None
    routing_metadata: dict[str, Any]
