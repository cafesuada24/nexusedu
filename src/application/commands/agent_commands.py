"""Command handlers for agent-related operations."""

import time
import uuid
from typing import TYPE_CHECKING, Any

from src.application.dtos.agent_dtos import AgentResponseDTO, RunAgentTaskCommand
from src.application.services.agent_metadata import AgentMetadataService
from src.domain.repositories.idempotency_repository import IdempotencyRepository
from src.core.logger import logger

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

    from src.infrastructure.agents.state import AgentState


class AgentCommandHandler:
    """Handler for agent-related commands."""

    def __init__(
        self,
        agent: 'CompiledStateGraph[AgentState, None, AgentState]',
        metadata_service: AgentMetadataService,
        idempotency_repo: IdempotencyRepository,
    ):
        self.agent = agent
        self.metadata_service = metadata_service
        self.idempotency_repo = idempotency_repo

    async def handle_run_agent_task(
        self, command: RunAgentTaskCommand
    ) -> AgentResponseDTO:
        """Execute the agent task command."""
        session_id = command.thread_id or uuid.uuid4()
        logger.set_context({'session_id': session_id, 'job_id': command.job_id})
        logger.info(f'Processing query: {command.query}')

        start_time = time.time()
        config = {
            'recursion_limit': 10,
            'configurable': {
                'thread_id': str(session_id),
                'max_concurrency': 3,
                'metadata_service': self.metadata_service,
                'user_role': command.user_dict.get('role', 'advisor'),
            },
        }

        try:
            inputs = {'messages': [{'role': 'user', 'content': command.query}]}
            final_state = await self.agent.ainvoke(inputs, config=config)

            execution_time = time.time() - start_time
            logger.info(f'Agent execution completed in {execution_time:.2f}s')

            if not final_state:
                raise ValueError('Agent returned an empty or invalid state.')

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

            return AgentResponseDTO(
                answer=answer,
                tables=tables if tables else None,
                session_id=session_id,
            )

        except Exception as e:
            logger.error(f'Agent execution failed: {e}', exc_info=True)
            raise
        finally:
            logger.clear_context()

    async def check_idempotency(self, key: uuid.UUID) -> bool:
        """Check if an idempotency key has been used."""
        return await self.idempotency_repo.check_key(key)

    async def record_idempotency(self, key: uuid.UUID) -> None:
        """Record a new idempotency key."""
        await self.idempotency_repo.record_key(key)
