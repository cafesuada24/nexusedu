"""Main endpoint for agent interaction."""

import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from langgraph.graph.state import CompiledStateGraph

from src.agents.state import AgentState
from src.api.dependencies.agent import get_agent
from src.api.models.request import QueryRequest
from src.api.models.response import QueryResponse
from src.telemetry.logger import logger

router = APIRouter(tags=['agent'])


@router.post('/query', response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    agent: Annotated[
        CompiledStateGraph[AgentState, None, AgentState],
        Depends(get_agent),
    ],
) -> QueryResponse:
    """Triggers the LangGraph agent to process a user query.

    Returns the final synthesized answer, tabular data, and visualizations.
    """
    session_id = request.thread_id or str(uuid.uuid4())
    logger.set_context({'session_id': session_id})
    logger.info(f'API: Processing query: {request.query}')

    start_time = time.time()
    config = {
        'recursion_limit': 50,
        'configurable': {'thread_id': session_id, 'max_concurrency': 3},
    }

    try:
        # Prepare the input state
        inputs = {'messages': [{'role': 'user', 'content': request.query}]}

        # Invoke the agent
        final_state = await agent.ainvoke(inputs, config=config)

        execution_time = time.time() - start_time
        logger.info(f'API: Agent execution completed in {execution_time:.2f}s')

        if not final_state:
            raise ValueError('Agent returned an empty or invalid state.')

        # Extract values from state with safety checks
        # 1. Answer (last message from the agent)
        messages = final_state.get('messages', [])
        answer = 'No response generated.'
        if messages:
            last_message = messages[-1]
            # Handle both BaseMessage objects and dict-based messages
            if hasattr(last_message, 'content'):
                answer = str(last_message.content)
            elif isinstance(last_message, dict) and 'content' in last_message:
                answer = str(last_message['content'])
            else:
                answer = str(last_message)

        # 2. Tabular Data (Tables)
        final_data = final_state.get('final_data')
        tables = None
        if final_data and isinstance(final_data, list) and len(final_data) > 0:
            first_result = final_data[0]
            if isinstance(first_result, dict) and 'data' in first_result:
                tables = [first_result['data']]

        return QueryResponse(
            answer=answer,
            tables=tables,
            visualizations=None,
            session_id=session_id,
        )

    except Exception as e:
        logger.error(f'API: Agent execution failed: {e}', exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        logger.clear_context()
