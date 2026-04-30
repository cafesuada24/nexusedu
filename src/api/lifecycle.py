"""Lifecycle management for the FastAPI application.

This module handles the startup and shutdown procedures, initializes global
state, and provides dependency injection providers for core services.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated, Any

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph.state import CompiledStateGraph
from psycopg_pool import ConnectionPool
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.database.sqlalchemy_repositories import (
    SqlAlchemyActivityRepository,
    SqlAlchemyAdvisorRepository,
    SqlAlchemyAlertRepository,
    SqlAlchemyEmailRepository,
    SqlAlchemyIdempotencyRepository,
    SqlAlchemyMetadataRepository,
    SqlAlchemyMetricsRepository,
    SqlAlchemyStatusHistoryRepository,
    SqlAlchemyStudentRepository,
)
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
from src.database.session import get_async_session
from src.domain.ports.repositories import (
    ActivityRepository,
    AdvisorRepository,
    AlertRepository,
    EmailRepository,
    IdempotencyRepository,
    MetadataRepository,
    MetricsRepository,
    StatusHistoryRepository,
    StudentRepository,
)
from src.domain.services.agent_metadata import AgentMetadataService
from src.domain.services.anomaly_engine import AnomalyEngine
from src.telemetry.logger import logger
from src.utils.collections import BoundedDict
from src.utils.env import getenv


@dataclass
class AppState:
    """State object held in the FastAPI app.state."""

    agent: CompiledStateGraph[AgentState, Any, AgentState]
    job_store: JobStore
    pool: ConnectionPool | None = None
    arq_pool: ArqRedis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages the startup and shutdown lifecycle of the FastAPI application."""
    load_dotenv()

    # ==== Unified DB Initialization ====
    logger.info('API Lifecycle: Initializing Unified Database...')
    await create_db_and_tables()

    # ==== Agent Checkpointer ====
    postgres_uri = getenv('POSTGRES_DB_URI')
    pool = None
    if postgres_uri:
        pool = ConnectionPool(conninfo=postgres_uri, max_size=20)
        checkpointer = PostgresSaver(pool)
        checkpointer.setup()
    else:
        checkpointer = MemorySaver()

    # ==== Agent ====
    agent = create_graph(checkpointer=checkpointer)

    # ==== JobStore ====
    jobs = BoundedDict[str, JobStatusResponse](maxsize=1000)

    # ==== ARQ Redis Pool ====
    try:
        arq_pool = await create_pool(
            RedisSettings(
                host=getenv('REDIS_HOST', 'localhost'),
                port=int(getenv('REDIS_PORT', '6379')),
            ),
        )
        logger.info('API Lifecycle: ARQ Redis Pool initialized.')
    except Exception as e:
        logger.warning(
            f'API Lifecycle: Could not connect to Redis: {e}. Background tasks will be disabled.'
        )
        arq_pool = None

    app.state.app_state = AppState(
        agent=agent,
        pool=pool,
        job_store=jobs,
        arq_pool=arq_pool,
    )

    yield

    if arq_pool:
        await arq_pool.close()
    if pool:
        pool.close()


# Repository Providers
async def get_student_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> StudentRepository:
    """Dependency provider for the StudentRepository."""
    return SqlAlchemyStudentRepository(session)


async def get_advisor_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AdvisorRepository:
    """Dependency provider for the AdvisorRepository."""
    return SqlAlchemyAdvisorRepository(session)


async def get_idempotency_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> IdempotencyRepository:
    """Dependency provider for the IdempotencyRepository."""
    return SqlAlchemyIdempotencyRepository(session)


async def get_email_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> EmailRepository:
    """Dependency provider for the EmailRepository."""
    return SqlAlchemyEmailRepository(session)


async def get_alert_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AlertRepository:
    """Dependency provider for the AlertRepository."""
    return SqlAlchemyAlertRepository(session)


async def get_activity_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ActivityRepository:
    """Dependency provider for the ActivityRepository."""
    return SqlAlchemyActivityRepository(session)


async def get_status_history_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> StatusHistoryRepository:
    """Dependency provider for the StatusHistoryRepository."""
    return SqlAlchemyStatusHistoryRepository(session)


async def get_metrics_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> MetricsRepository:
    """Dependency provider for the MetricsRepository."""
    return SqlAlchemyMetricsRepository(session)


async def get_metadata_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> MetadataRepository:
    """Dependency provider for the MetadataRepository."""
    return SqlAlchemyMetadataRepository(session)


# Service Providers
async def get_gamification_service(
    advisor_repo: Annotated[AdvisorRepository, Depends(get_advisor_repository)],
    student_repo: Annotated[StudentRepository, Depends(get_student_repository)],
) -> GamificationService:
    """Dependency provider for the GamificationService."""
    return GamificationService(advisor_repo, student_repo)


async def get_anomaly_engine(
    student_repo: Annotated[StudentRepository, Depends(get_student_repository)],
    activity_repo: Annotated[ActivityRepository, Depends(get_activity_repository)],
    history_repo: Annotated[
        StatusHistoryRepository, Depends(get_status_history_repository)
    ],
) -> AnomalyEngine:
    """Dependency provider for the AnomalyEngine."""
    return AnomalyEngine(student_repo, activity_repo, history_repo)


async def get_alert_service(
    alert_repo: Annotated[AlertRepository, Depends(get_alert_repository)],
    email_repo: Annotated[EmailRepository, Depends(get_email_repository)],
    student_repo: Annotated[StudentRepository, Depends(get_student_repository)],
    idempotency_repo: Annotated[
        IdempotencyRepository, Depends(get_idempotency_repository)
    ],
    gamification_service: Annotated[
        GamificationService, Depends(get_gamification_service)
    ],
) -> AlertService:
    """Dependency provider for the AlertService."""
    return AlertService(
        alert_repo,
        email_repo,
        student_repo,
        idempotency_repo,
        gamification_service,
    )


async def get_data_service(
    student_repo: Annotated[StudentRepository, Depends(get_student_repository)],
    activity_repo: Annotated[ActivityRepository, Depends(get_activity_repository)],
    anomaly_engine: Annotated[AnomalyEngine, Depends(get_anomaly_engine)],
) -> DataService:
    """Dependency provider for the DataService."""
    return DataService(student_repo, activity_repo, anomaly_engine)


async def get_metrics_service(
    metrics_repo: Annotated[MetricsRepository, Depends(get_metrics_repository)],
) -> MetricsService:
    """Dependency provider for the MetricsService."""
    return MetricsService(metrics_repo)


async def get_agent_metadata_service(
    metadata_repo: Annotated[MetadataRepository, Depends(get_metadata_repository)],
) -> AgentMetadataService:
    """Dependency provider for the AgentMetadataService."""
    return AgentMetadataService(metadata_repo)


def get_agent(request: Request) -> CompiledStateGraph[AgentState, Any, AgentState]:
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


async def get_query_service(
    agent: Annotated[
        CompiledStateGraph[AgentState, Any, AgentState], Depends(get_agent)
    ],
    metadata_service: Annotated[
        AgentMetadataService, Depends(get_agent_metadata_service)
    ],
) -> QueryService:
    """Dependency provider for the QueryService."""
    return QueryService(agent, metadata_service)


def get_arq_pool(request: Request) -> ArqRedis:
    """Dependency provider for the ARQ Redis pool."""
    state: AppState = request.app.state.app_state
    return state.arq_pool
