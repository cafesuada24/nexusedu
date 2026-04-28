"""Lifecycle management for the FastAPI application.

This module handles the startup and shutdown procedures, initializes global
state, and provides dependency injection providers for core services.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph.state import CompiledStateGraph
from psycopg_pool import ConnectionPool

from src.agents.agent import create_graph
from src.agents.state import AgentState
from src.api.auth import create_db_and_tables
from src.api.models.response import JobStatusResponse
from src.api.services.alerts import AlertService
from src.api.services.data import DataService
from src.api.services.query import QueryService
from src.api.types import JobStore
from src.database import DatabaseManager
from src.database.factory import algorithm_registry, engine_registry
from src.database.interfaces import AnomalyAlgorithm, DatabaseEngine
from src.telemetry.logger import logger
from src.types import BoundedDict
from src.utils.env import getenv


@dataclass
class AppState:
    """State object held in the FastAPI app.state."""

    db_manager: DatabaseManager[DatabaseEngine, AnomalyAlgorithm]
    agent: CompiledStateGraph[AgentState, None, AgentState]
    job_store: JobStore
    alert_service: AlertService
    query_service: QueryService
    data_service: DataService
    pool: ConnectionPool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages the startup and shutdown lifecycle of the FastAPI application."""
    load_dotenv()

    # ==== Auth DB ====
    logger.info('API Lifecycle: Initializing Auth Database...')
    await create_db_and_tables()

    # ==== DB ====
    logger.info('API Lifecycle: Initializing DatabaseManager...')
    db_manager = DatabaseManager[DatabaseEngine, AnomalyAlgorithm]()

    # Resolve engine and algorithm from environment or defaults
    engine_name = getenv('DB_ENGINE', 'duckdb')
    algo_name = getenv('DB_ALGORITHM', 'zscore')

    logger.info(f'API Lifecycle: Using engine={engine_name}, algorithm={algo_name}')

    db_manager.initialize(
        engine=engine_registry.create(engine_name),
        anomaly_algo=algorithm_registry.create(algo_name),
    )

    # Ensure schema is ready
    db_manager.initialize_schema()

    # ==== Services ====
    alert_service = AlertService(db_manager)
    data_service = DataService(db_manager)

    # ==== Agent Checkpointer ====
    postgres_uri = getenv('POSTGRES_DB_URI')
    pool = None
    if postgres_uri:
        logger.info('API Lifecycle: Initializing PostgresSaver checkpointer...')
        pool = ConnectionPool(conninfo=postgres_uri, max_size=20)
        checkpointer = PostgresSaver(pool)
        # Note: setup() is sync in PostgresSaver
        checkpointer.setup()
    else:
        logger.warning(
            'API Lifecycle: POSTGRES_DB_URI not found. Falling back to MemorySaver.',
        )
        checkpointer = MemorySaver()

    # ==== Agent ====
    logger.info('API Lifecycle: Agents...')
    agent = create_graph(checkpointer=checkpointer)

    # ==== Query Service ====
    query_service = QueryService(agent, db_manager)

    # ==== JobStore ====
    jobs = BoundedDict[str, JobStatusResponse](maxsize=1000)

    # Bind state to app
    app.state.app_state = AppState(
        db_manager=db_manager,
        agent=agent,
        pool=pool,
        job_store=jobs,
        alert_service=alert_service,
        query_service=query_service,
        data_service=data_service,
    )

    yield

    # SHUTDOWN: Cleanup resources
    logger.info('API Lifecycle: Shutting down...')
    if pool:
        pool.close()
    db_manager.close()


def get_dbmanager(
    request: Request,
) -> DatabaseManager[DatabaseEngine, AnomalyAlgorithm]:
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


def get_jobs_store(request: Request) -> JobStore:
    """Dependency provider for the JobStore.

    Returns:
        The JobStore
    """
    state: AppState = request.app.state.app_state
    return state.job_store


def get_alert_service(request: Request) -> AlertService:
    """Dependency provider for the AlertService."""
    state: AppState = request.app.state.app_state
    return state.alert_service


def get_query_service(request: Request) -> QueryService:
    """Dependency provider for the QueryService."""
    state: AppState = request.app.state.app_state
    return state.query_service


def get_data_service(request: Request) -> DataService:
    """Dependency provider for the DataService."""
    state: AppState = request.app.state.app_state
    return state.data_service
