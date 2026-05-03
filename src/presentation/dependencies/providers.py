"""Dependency injection providers for the application."""

from typing import Annotated, Any

from arq import ArqRedis
from fastapi import Depends, Request
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.agent_commands import AgentCommandHandler
from src.application.commands.alert_commands import AlertCommandHandler
from src.application.commands.data_commands import DataCommandHandler
from src.application.queries.alert_queries import AlertQueryHandler
from src.application.queries.metrics_queries import MetricsQueryHandler
from src.application.services.agent_metadata import AgentMetadataService
from src.domain.repositories.activity_repository import ActivityRepository
from src.domain.repositories.advisor_repository import AdvisorRepository
from src.domain.repositories.alert_repository import AlertRepository
from src.domain.repositories.case_repository import CaseRepository
from src.domain.repositories.email_repository import EmailRepository
from src.domain.repositories.idempotency_repository import IdempotencyRepository
from src.domain.repositories.job_repository import JobRepository
from src.domain.repositories.metadata_repository import MetadataRepository
from src.domain.repositories.metrics_repository import MetricsRepository
from src.domain.repositories.settings_repository import UserSettingsRepository
from src.domain.repositories.status_history_repository import StatusHistoryRepository
from src.domain.repositories.student_repository import StudentRepository
from src.domain.services.anomaly_engine.anomaly_engine import AnomalyEngine
from src.domain.services.anomaly_engine.zscore import ZScore
from src.domain.services.gamification import GamificationService
from src.infrastructure.agents.state import AgentState
from src.infrastructure.database.session import get_async_session
from src.infrastructure.extern.baml_drafting_service import BamlEmailDraftingService
from src.infrastructure.queue.arq_adapter import ArqTaskQueueAdapter
from src.infrastructure.repositories.sqlalchemy_repositories import (
    SqlAlchemyActivityRepository,
    SqlAlchemyAdvisorRepository,
    SqlAlchemyAlertRepository,
    SqlAlchemyCaseRepository,
    SqlAlchemyEmailRepository,
    SqlAlchemyIdempotencyRepository,
    SqlAlchemyJobRepository,
    SqlAlchemyMetadataRepository,
    SqlAlchemyMetricsRepository,
    SqlAlchemyStatusHistoryRepository,
    SqlAlchemyStudentRepository,
    SqlAlchemyUserSettingsRepository,
)


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


async def get_case_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> CaseRepository:
    """Dependency provider for the CaseRepository."""
    return SqlAlchemyCaseRepository(session)


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


async def get_job_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> JobRepository:
    """Dependency provider for the JobRepository."""
    return SqlAlchemyJobRepository(session)


async def get_user_settings_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> UserSettingsRepository:
    """Dependency provider for the UserSettingsRepository."""
    return SqlAlchemyUserSettingsRepository(session)


# Service Providers
def get_arq_pool(request: Request) -> ArqRedis:
    """Dependency provider for the ARQ Redis pool."""
    state = request.app.state.app_state
    return state.arq_pool


async def get_gamification_service() -> GamificationService:
    """Dependency provider for the GamificationService."""
    return GamificationService()


async def get_anomaly_engine() -> AnomalyEngine:
    """Dependency provider for the AnomalyEngine."""
    return ZScore()


async def get_alert_command_handler(
    student_repo: Annotated[StudentRepository, Depends(get_student_repository)],
    email_repo: Annotated[EmailRepository, Depends(get_email_repository)],
    case_repo: Annotated[CaseRepository, Depends(get_case_repository)],
    alert_repo: Annotated[AlertRepository, Depends(get_alert_repository)],
    advisor_repo: Annotated[AdvisorRepository, Depends(get_advisor_repository)],
    job_repo: Annotated[JobRepository, Depends(get_job_repository)],
    gamification_service: Annotated[
        GamificationService, Depends(get_gamification_service),
    ],
    arq_pool: Annotated[ArqRedis, Depends(get_arq_pool)],
) -> AlertCommandHandler:
    """Dependency provider for the AlertCommandHandler."""
    task_queue = ArqTaskQueueAdapter(arq_pool)
    return AlertCommandHandler(
        student_repo,
        email_repo,
        case_repo,
        alert_repo,
        advisor_repo,
        job_repo,
        gamification_service,
        task_queue,
        email_drafting_service=BamlEmailDraftingService(),
    )


async def get_alert_query_handler(
    alert_repo: Annotated[AlertRepository, Depends(get_alert_repository)],
    email_repo: Annotated[EmailRepository, Depends(get_email_repository)],
    student_repo: Annotated[StudentRepository, Depends(get_student_repository)],
    job_repo: Annotated[JobRepository, Depends(get_job_repository)],
    case_repo: Annotated[CaseRepository, Depends(get_case_repository)],
) -> AlertQueryHandler:
    """Dependency provider for the AlertQueryHandler."""
    return AlertQueryHandler(alert_repo, email_repo, student_repo, job_repo, case_repo)


async def get_data_command_handler(
    student_repo: Annotated[StudentRepository, Depends(get_student_repository)],
    activity_repo: Annotated[ActivityRepository, Depends(get_activity_repository)],
    history_repo: Annotated[
        StatusHistoryRepository, Depends(get_status_history_repository),
    ],
    case_repo: Annotated[CaseRepository, Depends(get_case_repository)],
    job_repo: Annotated[JobRepository, Depends(get_job_repository)],
    anomaly_engine: Annotated[AnomalyEngine, Depends(get_anomaly_engine)],
    alert_command_handler: Annotated[
        AlertCommandHandler, Depends(get_alert_command_handler),
    ],
) -> DataCommandHandler:
    """Dependency provider for the DataCommandHandler."""
    return DataCommandHandler(
        student_repo,
        activity_repo,
        history_repo,
        case_repo,
        job_repo,
        anomaly_engine,
        alert_command_handler,
    )


async def get_metrics_query_handler(
    metrics_repo: Annotated[MetricsRepository, Depends(get_metrics_repository)],
) -> MetricsQueryHandler:
    """Dependency provider for the MetricsQueryHandler."""
    return MetricsQueryHandler(metrics_repo)


async def get_agent_metadata_service(
    metadata_repo: Annotated[MetadataRepository, Depends(get_metadata_repository)],
) -> AgentMetadataService:
    """Dependency provider for the AgentMetadataService."""
    return AgentMetadataService(metadata_repo)


def get_agent(request: Request) -> CompiledStateGraph[AgentState, Any, AgentState]:
    """Dependency provider for the compiled LangGraph agent."""
    state = request.app.state.app_state
    return state.agent


async def get_agent_command_handler(
    agent: Annotated[
        CompiledStateGraph[AgentState, Any, AgentState], Depends(get_agent),
    ],
    metadata_service: Annotated[
        AgentMetadataService, Depends(get_agent_metadata_service),
    ],
    idempotency_repo: Annotated[
        IdempotencyRepository, Depends(get_idempotency_repository),
    ],
) -> AgentCommandHandler:
    """Dependency provider for the AgentCommandHandler."""
    return AgentCommandHandler(agent, metadata_service, idempotency_repo)
