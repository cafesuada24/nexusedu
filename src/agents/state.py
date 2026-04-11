import operator
from typing import Annotated, Any, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.graph import add_messages


class SQLTask(TypedDict):
    db_id: str
    dialect: str
    query_intent: str
    schema_hint: str
    message: HumanMessage


def last_value_reducer(x: Any, y: Any) -> Any:
    """Keep the last non-None value."""
    if y is None:
        return x
    return y


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    worker_states: dict[str, Any]
    tasks: list[dict]
    results: Annotated[list[dict], operator.add]
    final_data: Annotated[list[dict] | None, last_value_reducer]
    viz_json: Annotated[dict | str | None, last_value_reducer]
    decision_log: Annotated[list[dict], operator.add]  # Track agent reasoning
    retry_count: int  # For error handling and loops
    next_step: str
    discovery_context: str | None  # Store schema/discovery information
    routing_metadata: dict[str, Any]  # Store routing info like direct_response_draft or discovery_requests
