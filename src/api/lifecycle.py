import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from src.agents.agent import create_graph
from src.agents.state import AgentState
from src.database import DatabaseManager
from src.database.factory import algorithm_registry, engine_registry
from src.telemetry.logger import logger


@dataclass
class AppState:
    """State object held in the FastAPI app.state."""
    db_manager: DatabaseManager
    agent: CompiledStateGraph[AgentState, None, AgentState]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages the startup and shutdown lifecycle of the FastAPI application."""
    load_dotenv()

    # ==== DB ====
    logger.info('API Lifecycle: Initializing DatabaseManager...')
    db_manager = DatabaseManager()

    # Resolve engine and algorithm from environment or defaults
    engine_name = os.getenv('DB_ENGINE', 'duckdb')
    algo_name = os.getenv('DB_ALGORITHM', 'zscore')

    logger.info(f'API Lifecycle: Using engine={engine_name}, algorithm={algo_name}')

    db_manager.initialize(
        engine=engine_registry.create(engine_name),
        anomaly_algo=algorithm_registry.create(algo_name),
    )

    # Ensure schema is ready
    db_manager.initialize_schema()

    # ==== Agent ====
    logger.info('API Lifecycle: Agents...')
    memory = MemorySaver()
    agent = create_graph(checkpointer=memory)

    # Bind state to app
    app.state.app_state = AppState(
        db_manager=db_manager,
        agent=agent,
    )

    yield

    # SHUTDOWN: Cleanup resources
    logger.info('API Lifecycle: Shutting down DatabaseManager...')
    db_manager.close()


def get_dbmanager(request: Request) -> DatabaseManager:
    """Dependency provider for the DatabaseManager."""
    state: AppState = request.app.state.app_state
    return state.db_manager


def get_agent(request: Request) -> CompiledStateGraph[AgentState, None, AgentState]:
    """Dependency provider for the compiled LangGraph agent.

    Returns:
        The compiled LangGraph workflow with memory persistence.
    """
    state: AppState = request.app.state.app_state
    return state.agent
