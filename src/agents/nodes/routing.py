"""Conditional edge routing functions for the agent workflow."""

from typing import Literal

from langgraph.types import Send

from src.agents.state import MAX_DISCOVERY_DEPTH, AgentState
from src.telemetry.logger import logger


def route_after_sql(state: AgentState) -> Literal['email_agent', 'responder']:
    """Determines the next node after SQL execution tasks are complete."""
    routing = state.get('routing_metadata', {})
    next_action = routing.get('next_action_after_sql', 'RESPOND')

    logger.info(f'Routing (After SQL): Choosing path "{next_action}"')

    if next_action == 'EMAIL_DRAFT':
        return 'email_agent'

    return 'responder'

def route_planner(state: AgentState) -> str | list[Send]:
    """Determines the execution path from the planner node."""
    routing = state.get('routing_metadata', {})
    path = routing.get('path')

    logger.info(f'Routing (Planner): Choosing path "{path}"')

    if path == 'DISCOVERY_REQUIRED':
        depth = state.get('discovery_depth', 0)
        if depth >= MAX_DISCOVERY_DEPTH:
            logger.warning(
                f'Routing (Planner): Discovery depth limit reached ({depth}). Forcing direct response.',
            )
            return 'responder'
        return 'discovery'

    if path == 'DIRECT_ANSWER':
        return 'responder'

    if not state.get('tasks'):
        logger.warning(
            'Routing (Planner): Path was SQL_EXECUTION but no tasks found. Routing to responder.',
        )
        return 'responder'

    logger.info(
        f'Routing (Planner): Sending tasks to {len(state["tasks"])} SQL workers.',
    )

    return [
        Send(
            'sql_worker',
            {
                'db_id': task['db_id'],
                'dialect': task['dialect'],
                'query_intent': task['query_intent'],
                'schema_hint': task.get('schema_hint', ''),
                # 'message': f'Generate SQL for {task["db_id"]}.\n',
            },
        )
        for task in state['tasks']
    ]
