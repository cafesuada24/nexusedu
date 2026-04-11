"""Main endpoint for agent interaction."""

import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.agents.utils import extract_json_from_markdown
from src.api.dependencies.agent import get_agent
from src.api.models.request import QueryRequest
from src.api.models.response import QueryResponse
from src.telemetry.logger import logger

router = APIRouter(tags=["agent"])


@router.post("/query", response_model=QueryResponse)
async def process_query(
    request: QueryRequest, agent: Any = Depends(get_agent)
) -> QueryResponse:
    """Triggers the LangGraph agent to process a user query.

    Returns the final synthesized answer, tabular data, and visualizations.
    """
    session_id = request.thread_id or str(uuid.uuid4())
    logger.set_context({"session_id": session_id})
    logger.info(f"API: Processing query: {request.query}")

    start_time = time.time()
    config = {
        "recursion_limit": 50,
        "configurable": {"thread_id": session_id, "max_concurrency": 3},
    }

    try:
        # Prepare the input state
        from langchain_core.messages import HumanMessage

        inputs = {"messages": [HumanMessage(content=request.query)]}

        # Invoke the agent
        final_state = await agent.ainvoke(inputs, config=config)

        execution_time = time.time() - start_time
        logger.info(f"API: Agent execution completed in {execution_time:.2f}s")

        # Extract values from state
        # 1. Answer (last message from the agent)
        messages = final_state.get("messages", [])
        answer = messages[-1].content[-1]['text'] if messages else "No response generated."

        # 2. Tabular Data (Tables)
        # AgentState stores this in final_data which is a list[dict]
        # To support multiple tables (as per plural industry standard),
        # we wrap it in a list.
        final_data = final_state.get("final_data")
        tables = [final_data] if final_data else None

        # 3. Visualization JSON (List of Plotly objects)
        viz_raw = final_state.get("viz_json")
        visualizations = None
        if viz_raw and viz_raw != "NONE":
            viz_obj = None
            if isinstance(viz_raw, str):
                viz_obj = extract_json_from_markdown(viz_raw)
            else:
                viz_obj = viz_raw

            if viz_obj:
                visualizations = [viz_obj]

        return QueryResponse(
            answer=answer,
            tables=tables,
            visualizations=visualizations,
            session_id=session_id,
        )

    except Exception as e:
        logger.error(f"API: Agent execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        logger.clear_context()
