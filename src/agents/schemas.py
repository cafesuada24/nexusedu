from typing import Literal, Optional

from pydantic import BaseModel, Field


class DecisionLogEntry(BaseModel):
    """A log entry for a determiner's decision."""

    reasoning: str = Field(description='The reasoning behind the decision.')
    next_step: Literal['visualize', 'follow_up', 'finish'] = Field(
        description='The next step to take.',
    )
    metadata: dict[str, object] = Field(
        default_factory=dict,
        description='Additional metadata for the next step (e.g., recipient for email, format for export).',
    )


class DeterminerDecision(BaseModel):
    """The structured output for the determiner LLM's decision."""

    decision: DecisionLogEntry


class PlannerTask(BaseModel):
    """A single task for a SQL worker."""

    db_id: str = Field(description='The ID of the database to query.')
    dialect: str = Field(description='The SQL dialect to use (e.g., duckdb).')
    query_intent: str = Field(description='The specific data to retrieve from this database.')
    schema_hint: str = Field(default='', description='Optional hints about tables or columns to focus on.')


class PlannerOutput(BaseModel):
    """The structured output for the planner LLM."""

    tasks: list[PlannerTask] = Field(description='The list of parallel SQL tasks to execute.')


class SQLGeneration(BaseModel):
    """The structured output for the SQL generator LLM."""

    sql: str = Field(description='The generated SQL query.')
    explanation: str = Field(description='Brief explanation of the query logic.')


# --- Redesigned Planner Schemas ---

class DiscoveryRequest(BaseModel):
    """A request for schema discovery."""

    tool_name: Literal['get_db_list', 'list_tables', 'describe_table'] = Field(
        description='The name of the discovery tool to call.',
    )
    db_id: Optional[str] = Field(None, description='The database ID.')
    table_name: Optional[str] = Field(None, description='The table name if calling describe_table.')


class RouterPlan(BaseModel):
    """The structured output for the redesigned planner LLM."""

    path: Literal['SQL_EXECUTION', 'DIRECT_ANSWER', 'DISCOVERY_REQUIRED', 'EXTERNAL_TOOL'] = Field(
        description='The execution path chosen by the planner.',
    )
    tasks: Optional[list[PlannerTask]] = Field(
        None,
        description='The list of parallel SQL tasks to execute (required if path is SQL_EXECUTION).',
    )
    direct_response_draft: Optional[str] = Field(
        None,
        description='A draft of the direct response (required if path is DIRECT_ANSWER).',
    )
    discovery_requests: Optional[list[DiscoveryRequest]] = Field(
        None,
        description='The list of discovery tools to call (required if path is DISCOVERY_REQUIRED).',
    )
