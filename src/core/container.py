"""Centralized Dependency Injection Container."""

from functools import cached_property
from typing import Any

from arq import ArqRedis
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.agent_commands import AgentCommandHandler
from src.application.commands.case_commands import CaseCommandHandler
from src.application.commands.data_commands import DataCommandHandler
from src.application.interfaces.advisor_metrics_query_service import (
    AdvisorMetricsQueryService,
)
from src.application.interfaces.background_queue import BackgroundTaskQueue
from src.application.interfaces.case_query_service import CaseQueryService
from src.application.interfaces.gamification_query_service import (
    GamificationQueryService,
)
from src.application.interfaces.ledger_query_service import PointLedgerQueryService
from src.application.queries.advisor_queries import AdvisorQueryHandler
from src.application.queries.case_queries import CaseQueryHandler
from src.application.queries.metrics_queries import MetricsQueryHandler
from src.application.services.agent_metadata import AgentMetadataService
from src.application.services.event_publisher import TaskQueueEventPublisher
from src.core.config import config
from src.domain.repositories.activity_repository import ActivityRepository
from src.domain.repositories.advisor_repository import AdvisorRepository
from src.domain.repositories.appointment_repository import AppointmentRepository
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
from src.domain.services.email_sending import EmailSendingService
from src.domain.services.gamification import GamificationService
from src.infrastructure.extern.baml_drafting_service import BamlEmailDraftingService
from src.infrastructure.extern.email_sender import AioSmtpEmailSender
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
    SqlAlchemyAppointmentRepository,
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
from src.infrastructure.queue.outbox_adapter import TransactionalOutboxAdapter
from src.infrastructure.queue.outbox_processor import OutboxProcessor


class Container:
    """Dependency Injection Container for the application.

    Provides a centralized place to resolve dependencies for both
    the FastAPI application and the background worker.
    """

    def __init__(
        self,
        session: AsyncSession,
        redis_pool: ArqRedis | None = None,
        agent: CompiledStateGraph[Any, Any, Any] | None = None,
    ) -> None:
        """Initialize the container with core resources."""
        self.session = session
        self.redis_pool = redis_pool
        self.agent = agent

    # Repositories
    @cached_property
    def student_repo(self) -> StudentRepository:
        return SqlAlchemyStudentRepository(self.session)

    @cached_property
    def appointment_repo(self) -> AppointmentRepository:
        return SqlAlchemyAppointmentRepository(self.session)

    @cached_property
    def advisor_repo(self) -> AdvisorRepository:
        return SqlAlchemyAdvisorRepository(self.session)

    @cached_property
    def idempotency_repo(self) -> IdempotencyRepository:
        return SqlAlchemyIdempotencyRepository(self.session)

    @cached_property
    def email_repo(self) -> EmailRepository:
        return SqlAlchemyEmailRepository(self.session)

    @cached_property
    def case_repo(self) -> CaseRepository:
        return SqlAlchemyCaseRepository(self.session)

    @cached_property
    def activity_repo(self) -> ActivityRepository:
        return SqlAlchemyActivityRepository(self.session)

    @cached_property
    def status_history_repo(self) -> StatusHistoryRepository:
        return SqlAlchemyStatusHistoryRepository(self.session)

    @cached_property
    def metrics_repo(self) -> MetricsRepository:
        return SqlAlchemyMetricsRepository(self.session)

    @cached_property
    def metadata_repo(self) -> MetadataRepository:
        return SqlAlchemyMetadataRepository(self.session)

    @cached_property
    def job_repo(self) -> JobRepository:
        return SqlAlchemyJobRepository(self.session)

    @cached_property
    def user_settings_repo(self) -> UserSettingsRepository:
        return SqlAlchemyUserSettingsRepository(self.session)

    @cached_property
    def point_ledger_repo(self) -> PointLedgerRepository:
        return SqlAlchemyPointLedgerRepository(self.session)

    @cached_property
    def badge_repo(self) -> BadgeRepository:
        return SqlAlchemyBadgeRepository(self.session)

    # Services & Infrastructure
    @cached_property
    def gamification_service(self) -> GamificationService:
        return GamificationService()

    @cached_property
    def email_sending_service(self) -> EmailSendingService:
        return AioSmtpEmailSender(
            host=config.smtp_host,
            port=config.smtp_port,
            user=config.smtp_user,
            password=config.smtp_password,
            from_email=config.smtp_from_email,
        )

    @cached_property
    def anomaly_engine(self) -> AnomalyEngine:
        return ZScore()

    @cached_property
    def direct_task_queue(self) -> ArqTaskQueueAdapter:
        """Real background queue for immediate dispatching (used by poller)."""
        if self.redis_pool is None:
            raise ValueError('Redis pool is required for task queue operations.')
        return ArqTaskQueueAdapter(self.redis_pool)

    @cached_property
    def task_queue(self) -> BackgroundTaskQueue:
        """Primary queue that ensures transactional consistency via Outbox."""
        return TransactionalOutboxAdapter(self.session)

    @cached_property
    def outbox_processor(self) -> OutboxProcessor:
        """Processor to forward outbox events to the real background queue."""
        return OutboxProcessor(self.session, self.direct_task_queue)

    @cached_property
    def event_publisher(self) -> TaskQueueEventPublisher:
        return TaskQueueEventPublisher(self.task_queue)

    @cached_property
    def agent_metadata_service(self) -> AgentMetadataService:
        return AgentMetadataService(self.metadata_repo)

    # Query Services
    @cached_property
    def point_ledger_query_service(self) -> PointLedgerQueryService:
        return SqlAlchemyPointLedgerQueryService(session=self.session)

    @cached_property
    def gamification_query_service(self) -> GamificationQueryService:
        return SqlAlchemyGamificationQueryService(session=self.session)

    @cached_property
    def advisor_metrics_query_service(self) -> AdvisorMetricsQueryService:
        return SqlAlchemyAdvisorMetricsQueryService(session=self.session)

    @cached_property
    def case_query_service(self) -> CaseQueryService:
        return SqlAlchemyCaseQueryService(
            session=self.session,
            gamification_service=self.gamification_service,
        )

    # Command Handlers
    def get_case_command_handler(self) -> CaseCommandHandler:
        return CaseCommandHandler(
            self.student_repo,
            self.email_repo,
            self.case_repo,
            self.advisor_repo,
            self.appointment_repo,
            self.job_repo,
            self.task_queue,
            self.event_publisher,
            email_drafting_service=BamlEmailDraftingService(),
        )

    def get_data_command_handler(self) -> DataCommandHandler:
        return DataCommandHandler(
            self.student_repo,
            self.activity_repo,
            self.status_history_repo,
            self.case_repo,
            self.job_repo,
            self.anomaly_engine,
        )

    def get_agent_command_handler(self) -> AgentCommandHandler:
        if self.agent is None:
            raise ValueError('Agent is required for AgentCommandHandler.')
        return AgentCommandHandler(
            self.agent,
            self.agent_metadata_service,
            self.idempotency_repo,
        )

    # Query Handlers
    def get_advisor_query_handler(self) -> AdvisorQueryHandler:
        return AdvisorQueryHandler(
            advisor_repo=self.advisor_repo,
            point_ledger_query_service=self.point_ledger_query_service,
            gamification_query_service=self.gamification_query_service,
            advisor_metrics_query_service=self.advisor_metrics_query_service,
        )

    def get_case_query_handler(self) -> CaseQueryHandler:
        return CaseQueryHandler(
            case_query_service=self.case_query_service,
            advisor_repo=self.advisor_repo,
            case_repo=self.case_repo,
            email_repo=self.email_repo,
            student_repo=self.student_repo,
        )

    def get_metrics_query_handler(self) -> MetricsQueryHandler:
        return MetricsQueryHandler(self.metrics_repo)
