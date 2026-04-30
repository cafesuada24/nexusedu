"""Dependency injection providers for the application."""

from typing import Annotated, Any

from arq import ArqRedis
from fastapi import Depends, Request
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.repositories.interfaces import (
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
from src.infrastructure.agents.state import AgentState
from src.infrastructure.database.session import get_async_session
from src.infrastructure.repositories.sqlalchemy_repositories import (
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
from src.presentation.api.services.alerts import AlertService
from src.presentation.api.services.data import DataService
from src.presentation.api.services.gamification import GamificationService
from src.presentation.api.services.metrics import MetricsService
from src.presentation.api.services.query import QueryService


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
    """Dependency provider for the compiled LangGraph agent."""
    state = request.app.state.app_state
    return state.agent


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
    state = request.app.state.app_state
    return state.arq_pool
