"""Lifecycle management for the FastAPI application.

This module handles the startup and shutdown procedures, initializes global
state, and provides dependency injection providers for core services.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings
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
from src.api.services.gamification import GamificationService
from src.api.services.metrics import MetricsService
from src.api.services.query import QueryService
from src.api.types import JobStore
from src.database import DatabaseManager
from src.database.factory import algorithm_registry, engine_registry
from src.database.repositories.advisor_repository import AdvisorRepository
from src.database.repositories.student_repository import StudentRepository
from src.telemetry.logger import logger
from src.types import BoundedDict
from src.utils.env import getenv


@dataclass
class AppState:
    """State object held in the FastAPI app.state."""

    db_manager: DatabaseManager
    agent: CompiledStateGraph[AgentState, None, AgentState]
    job_store: JobStore
    alert_service: AlertService
    query_service: QueryService
    data_service: DataService
    metrics_service: MetricsService
    gamification_service: GamificationService
    pool: ConnectionPool | None = None
    arq_pool: ArqRedis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages the startup and shutdown lifecycle of the FastAPI application."""
    load_dotenv()

    # ==== Auth DB ====
    logger.info('API Lifecycle: Initializing Auth Database...')
    await create_db_and_tables()

    # ==== DB ====
    logger.info('API Lifecycle: Initializing DatabaseManager...')
    db_manager = DatabaseManager()

    # Resolve engine and algorithm from environment or defaults
    engine_name = getenv('DB_ENGINE', 'duckdb')
    algo_name = getenv('DB_ALGORITHM', 'zscore')

    logger.info(f'API Lifecycle: Using engine={engine_name}, algorithm={algo_name}')

    db_manager.initialize(
        engine=engine_registry.create(engine_name),
        anomaly_algo=algorithm_registry.create(algo_name),
    )

    # Ensure schema is ready
    await db_manager.initialize_schema_async()

    # ==== Repositories ====
    advisor_repo = AdvisorRepository(db_manager)
    student_repo = StudentRepository(db_manager)

    # ==== Services ====
    gamification_service = GamificationService(advisor_repo, student_repo)
    alert_service = AlertService(db_manager, gamification_service, student_repo)
    data_service = DataService(db_manager)
    metrics_service = MetricsService(db_manager)

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

    # ==== ARQ Redis Pool ====
    logger.info('API Lifecycle: Initializing ARQ Redis Pool...')
    arq_pool = await create_pool(
        RedisSettings(
            host=getenv('REDIS_HOST', 'localhost'),
            port=int(getenv('REDIS_PORT', '6379')),
        ),
    )

    # Bind state to app
    app.state.app_state = AppState(
        db_manager=db_manager,
        agent=agent,
        pool=pool,
        job_store=jobs,
        alert_service=alert_service,
        query_service=query_service,
        data_service=data_service,
        metrics_service=metrics_service,
        gamification_service=gamification_service,
        arq_pool=arq_pool,
    )

    yield

    # SHUTDOWN: Cleanup resources
    logger.info('API Lifecycle: Shutting down...')
    if arq_pool:
        await arq_pool.close()
    if pool:
        pool.close()
    db_manager.close()


def get_dbmanager(
    request: Request,
) -> DatabaseManager:
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


def get_metrics_service(request: Request) -> MetricsService:
    """Dependency provider for the MetricsService."""
    state: AppState = request.app.state.app_state
    return state.metrics_service


def get_gamification_service(request: Request) -> GamificationService:
    """Dependency provider for the GamificationService."""
    state: AppState = request.app.state.app_state
    return state.gamification_service


def get_arq_pool(request: Request) -> ArqRedis:
    """Dependency provider for the ARQ Redis pool."""
    state: AppState = request.app.state.app_state
    return state.arq_pool
