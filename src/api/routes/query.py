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

        # Extract values from state
        # 1. Answer (last message from the agent)
        messages = final_state.get('messages', [])
        if messages:
            last_message = messages[-1]
            if hasattr(last_message, 'content'):
                answer = last_message.content
            else:
                answer = str(last_message)
        else:
            answer = 'No response generated.'

        # 2. Tabular Data (Tables)
        final_data = final_state.get('final_data')
        tables = [final_data[0]['data']] if final_data and len(final_data) > 0 else None

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
