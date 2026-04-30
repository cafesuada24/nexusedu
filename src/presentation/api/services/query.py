"""Service layer for agent interaction."""

import time
import uuid
from typing import TYPE_CHECKING, Any

from src.domain.services.agent_metadata import AgentMetadataService
from src.presentation.schemas.response import QueryResponse
from src.telemetry.logger import logger

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

    from src.infrastructure.agents.state import AgentState


class QueryService:
    """Service for orchestrating agent queries."""

    def __init__(
        self,
        agent: 'CompiledStateGraph[AgentState, None, AgentState]',
        metadata_service: AgentMetadataService,
    ) -> None:
        """Initialize the QueryService.

        Args:
            agent: The compiled LangGraph agent.
            metadata_service: Service for database metadata retrieval.
        """
        self.agent = agent
        self.metadata_service = metadata_service

    async def run_agent_task(
        self,
        job_id: str,
        query: str,
        thread_id: str | None,
        user_dict: dict[str, Any],
    ) -> QueryResponse:
        """Encapsulates the LangGraph agent execution in a background task."""
        session_id = thread_id or str(uuid.uuid4())
        logger.set_context({'session_id': session_id, 'job_id': job_id})
        logger.info(f'QueryService: Processing query: {query}')

        start_time = time.time()
        # Reduce recursion_limit from 50 to 10 as per roadmap
        config = {
            'recursion_limit': 10,
            'configurable': {
                'thread_id': session_id,
                'max_concurrency': 3,
                'metadata_service': self.metadata_service,
                'user_role': user_dict.get('role', 'advisor'),
            },
        }

        try:
            # Prepare the input state
            inputs = {'messages': [{'role': 'user', 'content': query}]}

            # Invoke the agent
            final_state = await self.agent.ainvoke(inputs, config=config)

            execution_time = time.time() - start_time
            logger.info(
                f'QueryService: Agent execution completed in {execution_time:.2f}s'
            )

            if not final_state:
                raise ValueError('Agent returned an empty or invalid state.')

            # Extract values from state with safety checks
            messages = final_state.get('messages', [])
            answer = 'No response generated.'
            if messages:
                last_message = messages[-1]
                if hasattr(last_message, 'content'):
                    answer = str(last_message.content)
                elif isinstance(last_message, dict) and 'content' in last_message:
                    answer = str(last_message['content'])
                else:
                    answer = str(last_message)

            results = final_state.get('results', [])
            tables: list[list[dict[str, Any]]] = []
            if results and isinstance(results, list):
                for result in results:
                    if isinstance(result, dict) and 'data' in result:
                        data = result['data']
                        if (
                            isinstance(data, list)
                            and len(data) > 0
                            and isinstance(data[0], dict)
                            and 'error' in data[0]
                        ):
                            continue
                        tables.append(data)

            return QueryResponse(
                answer=answer,
                tables=tables if tables else None,
                visualizations=None,
                session_id=session_id,
            )

        except Exception as e:
            logger.error(f'QueryService: Agent execution failed: {e}', exc_info=True)
            raise
        finally:
            logger.clear_context()
