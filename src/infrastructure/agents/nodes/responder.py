"""Node that synthesizes all available context into a final response for the user."""

from typing import Any

from langchain_core.runnables import RunnableConfig

from src.infrastructure.agents.state import AgentState, MessageList
from src.infrastructure.agents.utils import ResultSummarizer
from src.infrastructure.extern.baml_client import b
from src.telemetry.logger import logger


class ResponderNode:
    """Synthesizes all available context into a final response for the user."""

    def __call__(self, state: AgentState, _config: RunnableConfig) -> dict[str, Any]:
        """Execute the responder node."""
        logger.info('Responder: Generating final response...')
        logger.debug(f'Responder State: {state}')

        context = self._summarize_result(state)

        human_messages = [
            m for m in state.get('messages', []) if m.get('role') == 'user'
        ]
        user_intent = (
            str(human_messages[-1]['content']) if human_messages else 'No intent found'
        )

        prompt = f"""
        <user_intent>
        {user_intent}
        </user_intent>

        <context>
        {context}
        </context>
        """

        logger.debug('Responder: Invoking LLM for final synthesis...')
        response = b.Respond(prompt)

        logger.info('Responder: Response generated.')
        return {'messages': [{'role': 'assistant', 'content': response}]}

    def _summarize_result(self, state: AgentState) -> str:
        """Summarize the results and context for the responder prompt."""
        results = state.get('results', [])
        routing = state.get('routing_metadata', {})
        direct_draft = routing.get('direct_response_draft')
        discovery_context = state.get('discovery_context')

        logger.info(
            f'Responder Context: results={bool(results)}, draft={bool(direct_draft)}, discovery={bool(discovery_context)}',
        )

        context_parts: list[str] = []
        if results:
            summary = ResultSummarizer.summarize(results)
            context_parts.append(f'<sql_result>:\n\t{summary}\n</sql_result>')
            logger.debug(f'Responder Result Summary length: {len(summary)}')
        if direct_draft:
            context_parts.append(f'<planner_draft>\n\t{direct_draft}\n</planner_draft>')
        if discovery_context:
            context_parts.append(f'<discovery>\n\t{discovery_context}\n</discovery>')

        return '\n\n'.join(context_parts)


responder_node = ResponderNode()
