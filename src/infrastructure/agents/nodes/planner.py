"""Node that determines the execution path based on user intent and current state."""

from typing import Any

from langchain_core.runnables import RunnableConfig

from src.infrastructure.agents.state import (
    MAX_MESSAGES,
    MAX_RESULTS,
    AgentState,
    RoutingMetadata,
)
from src.infrastructure.agents.utils import MessageSerializer
from src.infrastructure.extern.baml_client import b
from src.telemetry.logger import logger


class PlannerNode:
    """Determines the execution path based on user intent and current state."""

    def __call__(self, state: AgentState, _config: RunnableConfig) -> dict[str, Any]:
        """Execute the planner node."""
        logger.info('Planner: Executing...')
        logger.debug(f'Planner Input State: {state}')

        messages = state.get('messages', [])
        if len(messages) > MAX_MESSAGES:
            logger.warning(
                f'Planner: Message history exceeds limit ({len(messages)} > {MAX_MESSAGES}). Truncating...',
            )
            messages = messages[-MAX_MESSAGES:]

        message_yaml = MessageSerializer.to_yaml(messages)

        # Include discovery context in the prompt if available
        if state.get('discovery_context'):
            logger.info('Planner: Incorporating discovery context.')
            message_yaml += f'\n\n<discovery_context>\n{state["discovery_context"]}\n</discovery_context>'
            logger.debug(
                f'Discovery Context Length: {len(state["discovery_context"] or "")}'
            )

        logger.debug('Planner: Invoking LLM...')
        plan = b.PlanNextStep(message_yaml)

        logger.info(f'Planner Path Decision: {plan.path}')
        logger.log_event(
            'planner_output',
            {
                'path': plan.path,
                'tasks_count': len(plan.tasks) if plan.tasks else 0,
                'discovery_requests_count': len(plan.discovery_requests)
                if plan.discovery_requests
                else 0,
                'has_direct_response': bool(plan.direct_response_draft),
            },
        )

        routing_metadata: RoutingMetadata = {
            'path': plan.path,
            'direct_response_draft': plan.direct_response_draft,
            'discovery_requests': plan.discovery_requests or [],
            'next_action_after_sql': plan.next_action_after_sql or 'RESPOND',
        }

        update: dict[str, Any] = {
            'messages': messages,  # Update with truncated messages
            'routing_metadata': routing_metadata,
        }

        # Reset results and data if this is a fresh query (not a follow-up loop)
        if state.get('next_step') != 'follow_up':
            logger.info('Planner: Fresh query detected, resetting results.')
            update['results'] = None
        else:
            logger.info('Planner: Follow-up iteration, preserving existing results.')
            results = state.get('results', [])
            if results and len(results) > MAX_RESULTS:
                logger.warning(
                    f'Planner: Results list exceeds limit ({len(results)} > {MAX_RESULTS}). Truncating...',
                )
                update['results'] = results[-MAX_RESULTS:]

        if plan.path == 'SQL_EXECUTION' and plan.tasks:
            logger.debug(f'Planner Tasks: {plan.tasks}')
            update['tasks'] = [task.model_dump() for task in plan.tasks]
        else:
            update['tasks'] = []

        return update


planner_node = PlannerNode()
