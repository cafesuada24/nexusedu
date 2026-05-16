"""Dependency injection providers for the application."""

from typing import Annotated

from arq import ArqRedis
from fastapi import Depends, Request
from fastapi.requests import HTTPConnection
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.case_commands import CaseCommandHandler
from src.application.commands.data_commands import DataCommandHandler
from src.application.commands.schedule_commands import ScheduleCommandHandler
from src.application.interfaces.advisor_metrics_query_service import (
    AdvisorMetricsQueryService,
)
from src.application.interfaces.case_query_service import CaseQueryService
from src.application.interfaces.gamification_query_service import (
    GamificationQueryService,
)
from src.application.interfaces.ledger_query_service import PointLedgerQueryService
from src.application.interfaces.student_query_service import StudentQueryService
from src.application.interfaces.unit_of_work import UnitOfWork
from src.application.queries.advisor_queries import AdvisorQueryHandler
from src.application.queries.case_queries import CaseQueryHandler
from src.application.queries.metrics_queries import MetricsQueryHandler
from src.application.queries.student_queries import StudentQueryHandler
from src.core.container import Container
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
from src.domain.services.gamification import GamificationService
from src.infrastructure.database.session import get_async_session
from src.infrastructure.queue.outbox_processor import OutboxProcessor


async def get_container(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    connection: HTTPConnection,
) -> Container:
    """Dependency provider for the DI Container."""
    app_state = getattr(connection.app.state, 'app_state', None)
    redis_pool = getattr(app_state, 'arq_pool', None) if app_state else None

    return Container(session=session, redis_pool=redis_pool)


# Repository Providers
async def get_student_repository(
    container: Annotated[Container, Depends(get_container)],
) -> StudentRepository:
    """Dependency provider for the StudentRepository."""
    return container.student_repo


async def get_advisor_repository(
    container: Annotated[Container, Depends(get_container)],
) -> AdvisorRepository:
    """Dependency provider for the AdvisorRepository."""
    return container.advisor_repo


async def get_idempotency_repository(
    container: Annotated[Container, Depends(get_container)],
) -> IdempotencyRepository:
    """Dependency provider for the IdempotencyRepository."""
    return container.idempotency_repo


async def get_email_repository(
    container: Annotated[Container, Depends(get_container)],
) -> EmailRepository:
    """Dependency provider for the EmailRepository."""
    return container.email_repo


async def get_case_repository(
    container: Annotated[Container, Depends(get_container)],
) -> CaseRepository:
    """Dependency provider for the CaseRepository."""
    return container.case_repo


async def get_activity_repository(
    container: Annotated[Container, Depends(get_container)],
) -> ActivityRepository:
    """Dependency provider for the ActivityRepository."""
    return container.activity_repo


async def get_status_history_repository(
    container: Annotated[Container, Depends(get_container)],
) -> StatusHistoryRepository:
    """Dependency provider for the StatusHistoryRepository."""
    return container.status_history_repo


async def get_metrics_repository(
    container: Annotated[Container, Depends(get_container)],
) -> MetricsRepository:
    """Dependency provider for the MetricsRepository."""
    return container.metrics_repo


async def get_metadata_repository(
    container: Annotated[Container, Depends(get_container)],
) -> MetadataRepository:
    """Dependency provider for the MetadataRepository."""
    return container.metadata_repo


async def get_job_repository(
    container: Annotated[Container, Depends(get_container)],
) -> JobRepository:
    """Dependency provider for the JobRepository."""
    return container.job_repo


async def get_user_settings_repository(
    container: Annotated[Container, Depends(get_container)],
) -> UserSettingsRepository:
    """Dependency provider for the UserSettingsRepository."""
    return container.user_settings_repo


async def get_point_ledger_repository(
    container: Annotated[Container, Depends(get_container)],
) -> PointLedgerRepository:
    """Dependency provider for the PointLedgerRepository."""
    return container.point_ledger_repo


async def get_badge_repository(
    container: Annotated[Container, Depends(get_container)],
) -> BadgeRepository:
    """Dependency provider for the BadgeRepository."""
    return container.badge_repo


# Service Providers
def get_arq_pool(request: Request) -> ArqRedis:
    """Dependency provider for the ARQ Redis pool."""
    state = request.app.state.app_state
    return state.arq_pool


async def get_gamification_service(
    container: Annotated[Container, Depends(get_container)],
) -> GamificationService:
    """Dependency provider for the GamificationService."""
    return container.gamification_service


async def get_anomaly_engine(
    container: Annotated[Container, Depends(get_container)],
) -> AnomalyEngine:
    """Dependency provider for the AnomalyEngine."""
    return container.anomaly_engine


async def get_point_ledger_query_service(
    container: Annotated[Container, Depends(get_container)],
) -> PointLedgerQueryService:
    return container.point_ledger_query_service


async def get_gamification_query_service(
    container: Annotated[Container, Depends(get_container)],
) -> GamificationQueryService:
    return container.gamification_query_service


async def get_advisor_metrics_query_service(
    container: Annotated[Container, Depends(get_container)],
) -> AdvisorMetricsQueryService:
    return container.advisor_metrics_query_service


async def get_case_query_service(
    container: Annotated[Container, Depends(get_container)],
) -> CaseQueryService:
    """Dependency provider for the CaseQueryService."""
    return container.case_query_service


async def get_student_query_service(
    container: Annotated[Container, Depends(get_container)],
) -> StudentQueryService:
    """Dependency provider for the StudentQueryService."""
    return container.student_query_service


async def get_unit_of_work(
    container: Annotated[Container, Depends(get_container)],
) -> UnitOfWork:
    """Dependency provider for the UnitOfWork."""
    return container.uow


async def get_case_command_handler(
    container: Annotated[Container, Depends(get_container)],
) -> CaseCommandHandler:
    """Dependency provider for the CaseCommandHandler."""
    return container.get_case_command_handler()


async def get_outbox_processor(
    container: Annotated[Container, Depends(get_container)],
) -> OutboxProcessor:
    """Dependency provider for the OutboxProcessor."""
    return container.outbox_processor


async def get_schedule_command_handler(
    container: Annotated[Container, Depends(get_container)],
) -> ScheduleCommandHandler:
    """Dependency provider for the ScheduleCommandHandler."""
    return container.get_schedule_command_handler()


async def get_advisor_query_handler(
    container: Annotated[Container, Depends(get_container)],
) -> AdvisorQueryHandler:
    """Dependency provider for the AdvisorQueryHandler."""
    return container.get_advisor_query_handler()


async def get_case_query_handler(
    container: Annotated[Container, Depends(get_container)],
) -> CaseQueryHandler:
    """Dependency provider for the CaseQueryHandler."""
    return container.get_case_query_handler()


async def get_data_command_handler(
    container: Annotated[Container, Depends(get_container)],
) -> DataCommandHandler:
    """Dependency provider for the DataCommandHandler."""
    return container.get_data_command_handler()


async def get_metrics_query_handler(
    container: Annotated[Container, Depends(get_container)],
) -> MetricsQueryHandler:
    """Dependency provider for the MetricsQueryHandler."""
    return container.get_metrics_query_handler()


async def get_student_query_handler(
    container: Annotated[Container, Depends(get_container)],
) -> StudentQueryHandler:
    """Dependency provider for the StudentQueryHandler."""
    return container.get_student_query_handler()
