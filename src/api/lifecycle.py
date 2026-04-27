from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Required, TypedDict

from dotenv import load_dotenv
from fastapi import FastAPI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from src.agents.agent import create_graph
from src.agents.state import AgentState
from src.database import DatabaseManager
from src.database.algorithms.zscore import DuckDBZScoreAnomalyAlgorithm
from src.database.engines.duckdb_engine import DuckDBEngine
from src.telemetry.logger import logger


class GlobalState(TypedDict):
    db_manager: DatabaseManager
    agent_with_memory: CompiledStateGraph[AgentState, None, AgentState, AgentState]


_state: GlobalState | None = None


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Manages the startup and shutdown lifecycle of the FastAPI application."""
    # STARTUP: Initialize Database
    global _state
    load_dotenv()

    # ==== DB ====
    logger.info('API Lifecycle: Initializing DatabaseManager...')
    db_manager = DatabaseManager()
    db_manager.initialize(
        engine=DuckDBEngine(),
        anomaly_algo=DuckDBZScoreAnomalyAlgorithm(),
    )
    # Optional: ensure schema is ready
    db_manager.initialize_schema()

    # ==== Agent ====
    logger.info('API Lifecycle: Agents...')
    memory = MemorySaver()

    agent_with_memory = create_graph(checkpointer=memory)
    _state = {
        'db_manager': db_manager,
        'agent_with_memory': agent_with_memory,
    }

    yield

    # SHUTDOWN: Cleanup resources
    logger.info('API Lifecycle: Shutting down DatabaseManager...')
    db_manager.close()
    del db_manager


def get_dbmanager() -> DatabaseManager:
    if _state is None:
        raise RuntimeError('global state is not initialized')
    return _state['db_manager']

def get_agent() -> CompiledStateGraph[AgentState, None, AgentState, AgentState]:
    """Dependency provider for the compiled LangGraph agent.

    Returns:
        The compiled LangGraph workflow with memory persistence.
    """
    if _state is None:
        raise RuntimeError('global state is not initialized')
    return _state['agent_with_memory']
