"""Node that determines the execution path based on user intent and current state."""

from typing import Any

from langchain_core.messages import AIMessage, BaseMessage

from src.agents.state import AgentState, MessageList
from src.baml_client import b
from src.prompts.loader import load_prompt
from src.telemetry.logger import logger

PLANNER_SYSTEM_PROMPT = load_prompt('src/prompts/v1/planner/system.txt')


def _msg_to_yaml(msg: BaseMessage) -> str:
    role = 'ai_response' if isinstance(msg, AIMessage) else 'human_message'
    return f'<{role}>\n{msg.content}\n<\\{role}>'


def _msg_list_to_yaml(state: MessageList) -> str:
    return '\n\n'.join(_msg_to_yaml(msg) for msg in state)


def planner(state: AgentState) -> dict[str, Any]:
    """Node that determines the execution path based on user intent and current state."""
    logger.info('Planner: Executing...')
    logger.debug(f'Planner Input State: {state}')

    message = _msg_list_to_yaml(state['messages'])

    # Include discovery context in the prompt if available
    discovery_info = ''
    if state.get('discovery_context'):
        logger.info('Planner: Incorporating discovery context.')
        message += f'\n\n<discovery_context>\n{state["discovery_context"]}\n</discovery_context>'
        logger.debug(f'Discovery Context Length: {len(state["discovery_context"])}')

    logger.debug('Planner: Invoking LLM...')
    plan = b.PlanNextStep(message)

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

    update: dict[str, Any] = {
        'routing_metadata': {
            'path': plan.path,
            'direct_response_draft': plan.direct_response_draft,
            'discovery_requests': plan.discovery_requests or [],
            'next_action_after_sql': plan.next_action_after_sql or 'RESPOND',
        },
    }

    # Reset results and data if this is a fresh query (not a follow-up loop)
    if state.get('next_step') != 'follow_up':
        logger.info('Planner: Fresh query detected, resetting results.')
        update['results'] = None
    else:
        logger.info('Planner: Follow-up iteration, preserving existing results.')

    if plan.path == 'SQL_EXECUTION' and plan.tasks:
        logger.debug(f'Planner Tasks: {plan.tasks}')
        update['tasks'] = [task.model_dump() for task in plan.tasks]
    else:
        update['tasks'] = []

    return update
