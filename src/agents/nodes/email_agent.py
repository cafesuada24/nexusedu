"""Node for generating personalized email drafts based on student data."""

from typing import Any

from langchain_core.runnables import RunnableConfig

from src.agents.state import AgentState
from src.agents.utils import ResultSummarizer
from src.baml_client import b
from src.telemetry.logger import logger


class EmailAgentNode:
    """Generates personalized email drafts based on student data."""

    def __call__(self, state: AgentState, _config: RunnableConfig) -> dict[str, Any]:
        """Execute the email agent node."""
        logger.info('Email Agent: Generating draft...')

        results = state.get('results', [])
        summary = ResultSummarizer.summarize(results)

        human_messages = [
            m for m in state.get('messages', []) if m.get('role') == 'user'
        ]
        user_intent = (
            str(human_messages[-1]['content'])
            if human_messages
            else 'Generate nudge email'
        )

        logger.debug('Email Agent: Invoking LLM for email drafting...')
        response = b.GenerateDraftEmail(user_intent, summary)

        logger.info('Email Agent: Draft generated.')
        return {'messages': [{'role': 'assistant', 'content': response}]}


email_agent_node = EmailAgentNode()
