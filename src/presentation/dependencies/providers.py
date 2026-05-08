"""Dependency injection providers for the application."""

from typing import Annotated, Any

from arq import ArqRedis
from fastapi import Depends, Request
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.agent_commands import AgentCommandHandler
from src.application.commands.case_commands import CaseCommandHandler
from src.application.commands.data_commands import DataCommandHandler
from src.application.interfaces.advisor_metrics_query_service import (
    AdvisorMetricsQueryService,
)
from src.application.interfaces.case_query_service import CaseQueryService
from src.application.interfaces.gamification_query_service import (
    GamificationQueryService,
)
from src.application.interfaces.ledger_query_service import PointLedgerQueryService
from src.application.queries.advisor_queries import AdvisorQueryHandler
from src.application.queries.case_queries import CaseQueryHandler
from src.application.queries.metrics_queries import MetricsQueryHandler
from src.application.services.agent_metadata import AgentMetadataService
from src.domain.repositories.activity_repository import ActivityRepository
from src.domain.repositories.advisor_repository import AdvisorRepository
from src.domain.repositories.badge_repository import BadgeRepository
from src.domain.repositories.case_repository import CaseRepository
from src.domain.repositories.email_repository import EmailRepository
from src.domain.repositories.idempotency_repository import IdempotencyRepository
from src.domain.repositories.job_repository import JobRepository
from src.domain.repositories.metadata_repository import MetadataRepository
from src.domain.repositories.metrics_repository import MetricsRepository
from src.domain.repositories.point_ledger_repository import PointLedgerRepository
from src.domain.repositories.settings_repository import UserSettingsRepository
from src.domain.repositories.status_history_repository import StatusHistoryRepository
from src.domain.repositories.student_repository import StudentRepository
from src.domain.services.anomaly_engine.anomaly_engine import AnomalyEngine
from src.domain.services.anomaly_engine.zscore import ZScore
from src.domain.services.gamification import GamificationService
from src.infrastructure.agents.state import AgentState
from src.infrastructure.database.session import get_async_session
from src.infrastructure.extern.baml_drafting_service import BamlEmailDraftingService
from src.infrastructure.persistence.query_services.advisor_metrics_query_service import (
    SqlAlchemyAdvisorMetricsQueryService,
)
from src.infrastructure.persistence.query_services.case_query_service import (
    SqlAlchemyCaseQueryService,
)
from src.infrastructure.persistence.query_services.gamification_query_service import (
    SqlAlchemyGamificationQueryService,
)
from src.infrastructure.persistence.query_services.point_ledger_query_service import (
    SqlAlchemyPointLedgerQueryService,
)
from src.infrastructure.persistence.repositories.sqlalchemy_repositories import (
    SqlAlchemyActivityRepository,
    SqlAlchemyAdvisorRepository,
    SqlAlchemyBadgeRepository,
    SqlAlchemyCaseRepository,
    SqlAlchemyEmailRepository,
    SqlAlchemyIdempotencyRepository,
    SqlAlchemyJobRepository,
    SqlAlchemyMetadataRepository,
    SqlAlchemyMetricsRepository,
    SqlAlchemyPointLedgerRepository,
    SqlAlchemyStatusHistoryRepository,
    SqlAlchemyStudentRepository,
    SqlAlchemyUserSettingsRepository,
)
from src.infrastructure.queue.arq_adapter import ArqTaskQueueAdapter


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


async def get_point_ledger_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> PointLedgerRepository:
    """Dependency provider for the PointLedgerRepository."""
    return SqlAlchemyPointLedgerRepository(session)


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


async def get_badge_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> BadgeRepository:
    """Dependency provider for the BadgeRepository."""
    return SqlAlchemyBadgeRepository(session)


# async def get_alert_command_handler(
#     student_repo: Annotated[StudentRepository, Depends(get_student_repository)],
#     email_repo: Annotated[EmailRepository, Depends(get_email_repository)],
#     case_repo: Annotated[CaseRepository, Depends(get_case_repository)],
#     alert_repo: Annotated[AlertRepository, Depends(get_alert_repository)],
#     advisor_repo: Annotated[AdvisorRepository, Depends(get_advisor_repository)],
#     job_repo: Annotated[JobRepository, Depends(get_job_repository)],
#     gamification_service: Annotated[
#         GamificationService, Depends(get_gamification_service),
#     ],
#     arq_pool: Annotated[ArqRedis, Depends(get_arq_pool)],
#     badge_repo: Annotated[BadgeRepository, Depends(get_badge_repository)],
# ) -> AlertCommandHandler:
#     """Dependency provider for the AlertCommandHandler."""
#     task_queue = ArqTaskQueueAdapter(arq_pool)
#     return AlertCommandHandler(
#         student_repo,
#         email_repo,
#         case_repo,
#         alert_repo,
#         advisor_repo,
#         job_repo,
#         gamification_service,
#         task_queue,
#         email_drafting_service=BamlEmailDraftingService(),
#         badge_repo=badge_repo,
#     )


async def get_point_ledger_query_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> PointLedgerQueryService:
    return SqlAlchemyPointLedgerQueryService(session=session)


async def get_gamification_query_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> GamificationQueryService:
    return SqlAlchemyGamificationQueryService(session=session)


async def get_advisor_metrics_query_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AdvisorMetricsQueryService:
    return SqlAlchemyAdvisorMetricsQueryService(session=session)


async def get_case_query_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    gamification_service: Annotated[
        GamificationService,
        Depends(get_gamification_service),
    ],
) -> CaseQueryService:
    """Dependency provider for the CaseQueryService."""
    return SqlAlchemyCaseQueryService(
        session=session,
        gamification_service=gamification_service,
    )


async def get_case_command_handler(
    student_repo: Annotated[StudentRepository, Depends(get_student_repository)],
    email_repo: Annotated[EmailRepository, Depends(get_email_repository)],
    case_repo: Annotated[CaseRepository, Depends(get_case_repository)],
    advisor_repo: Annotated[AdvisorRepository, Depends(get_advisor_repository)],
    job_repo: Annotated[JobRepository, Depends(get_job_repository)],
    gamification_service: Annotated[
        GamificationService,
        Depends(get_gamification_service),
    ],
    arq_pool: Annotated[ArqRedis, Depends(get_arq_pool)],
    badge_repo: Annotated[BadgeRepository, Depends(get_badge_repository)],
    point_ledger_repo: Annotated[
        PointLedgerRepository,
        Depends(get_point_ledger_repository),
    ],
) -> CaseCommandHandler:
    """Dependency provider for the CaseCommandHandler."""
    task_queue = ArqTaskQueueAdapter(arq_pool)
    return CaseCommandHandler(
        student_repo,
        email_repo,
        case_repo,
        advisor_repo,
        job_repo,
        gamification_service,
        task_queue,
        email_drafting_service=BamlEmailDraftingService(),
        badge_repo=badge_repo,
        point_ledger_repo=point_ledger_repo,
    )


async def get_advisor_query_handler(
    advisor_repo: Annotated[AdvisorRepository, Depends(get_advisor_repository)],
    point_ledger_query_service: Annotated[
        PointLedgerQueryService,
        Depends(get_point_ledger_query_service),
    ],
    gamification_query_service: Annotated[
        GamificationQueryService,
        Depends(get_gamification_query_service),
    ],
    advisor_metrics_query_service: Annotated[
        AdvisorMetricsQueryService,
        Depends(get_advisor_metrics_query_service),
    ],
) -> AdvisorQueryHandler:
    """Dependency provider for the AdvisorQueryHandler."""
    return AdvisorQueryHandler(
        advisor_repo=advisor_repo,
        point_ledger_query_service=point_ledger_query_service,
        gamification_query_service=gamification_query_service,
        advisor_metrics_query_service=advisor_metrics_query_service,
    )


async def get_case_query_handler(
    case_query_service: Annotated[CaseQueryService, Depends(get_case_query_service)],
    advisor_repo: Annotated[AdvisorRepository, Depends(get_advisor_repository)],
    case_repo: Annotated[CaseRepository, Depends(get_case_repository)],
    student_repo: Annotated[StudentRepository, Depends(get_student_repository)],
    email_repo: Annotated[EmailRepository, Depends(get_email_repository)],
) -> CaseQueryHandler:
    """Dependency provider for the CaseQueryHandler."""
    return CaseQueryHandler(
        case_query_service=case_query_service,
        advisor_repo=advisor_repo,
        case_repo=case_repo,
        email_repo=email_repo,
        student_repo=student_repo,
    )


async def get_data_command_handler(
    student_repo: Annotated[StudentRepository, Depends(get_student_repository)],
    activity_repo: Annotated[ActivityRepository, Depends(get_activity_repository)],
    history_repo: Annotated[
        StatusHistoryRepository,
        Depends(get_status_history_repository),
    ],
    case_repo: Annotated[CaseRepository, Depends(get_case_repository)],
    job_repo: Annotated[JobRepository, Depends(get_job_repository)],
    anomaly_engine: Annotated[AnomalyEngine, Depends(get_anomaly_engine)],
    case_command_handler: Annotated[
        CaseCommandHandler,
        Depends(get_case_command_handler),
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
        case_command_handler,
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
        CompiledStateGraph[AgentState, Any, AgentState],
        Depends(get_agent),
    ],
    metadata_service: Annotated[
        AgentMetadataService,
        Depends(get_agent_metadata_service),
    ],
    idempotency_repo: Annotated[
        IdempotencyRepository,
        Depends(get_idempotency_repository),
    ],
) -> AgentCommandHandler:
    """Dependency provider for the AgentCommandHandler."""
    return AgentCommandHandler(agent, metadata_service, idempotency_repo)
