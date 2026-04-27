"""Main endpoint for agent interaction."""

import time
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from langgraph.graph.state import CompiledStateGraph

from src.agents.state import AgentState
from src.api.lifecycle import get_agent, get_dbmanager
from src.api.models.request import QueryRequest
from src.api.models.response import (
    JobAcceptedResponse,
    JobStatusResponse,
    QueryResponse,
)
from src.api.utils.jobs_store import _jobs
from src.database import DatabaseManager
from src.telemetry.logger import logger

router = APIRouter(tags=['agent'])


async def _run_agent_task(
    job_id: str,
    query: str,
    thread_id: str | None,
    agent: CompiledStateGraph[AgentState, None, AgentState],
    db_manager: DatabaseManager,
) -> None:
    """Encapsulates the LangGraph agent execution in a background task."""
    session_id = thread_id or str(uuid.uuid4())
    logger.set_context({'session_id': session_id, 'job_id': job_id})
    logger.info(f'API (BG): Processing query: {query}')

    start_time = time.time()
    config = {
        'recursion_limit': 50,
        'configurable': {
            'thread_id': session_id,
            'max_concurrency': 3,
            'db_manager': db_manager,
        },
    }

    try:
        # Prepare the input state
        inputs = {'messages': [{'role': 'user', 'content': query}]}

        # Invoke the agent
        final_state = await agent.ainvoke(inputs, config=config)

        execution_time = time.time() - start_time
        logger.info(f'API (BG): Agent execution completed in {execution_time:.2f}s')

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
        tables = []
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

        # Update job status to completed
        _jobs[job_id] = JobStatusResponse(
            job_id=job_id,
            status='completed',
            result=QueryResponse(
                answer=answer,
                tables=tables if tables else None,
                visualizations=None,
                session_id=session_id,
            ),
        )

    except Exception as e:
        logger.error(f'API (BG): Agent execution failed: {e}', exc_info=True)
        _jobs[job_id] = JobStatusResponse(
            job_id=job_id,
            status='failed',
            error=str(e),
        )
    finally:
        logger.clear_context()


@router.post('/query', response_model=JobAcceptedResponse, status_code=202)
async def process_query(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    agent: Annotated[
        CompiledStateGraph[AgentState, None, AgentState],
        Depends(get_agent),
    ],
    db_manager: Annotated[DatabaseManager, Depends(get_dbmanager)],
) -> JobAcceptedResponse:
    """Triggers the LangGraph agent in the background.

    Returns a job_id immediately for status polling.
    """
    job_id = str(uuid.uuid4())

    # Initialize job status
    _jobs[job_id] = JobStatusResponse(job_id=job_id, status='processing')

    # Schedule background task
    background_tasks.add_task(
        _run_agent_task,
        job_id=job_id,
        query=request.query,
        thread_id=request.thread_id,
        agent=agent,
        db_manager=db_manager,
    )

    return JobAcceptedResponse(job_id=job_id, status='processing')
