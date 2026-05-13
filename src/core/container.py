"""Centralized Dependency Injection Container."""

from functools import cached_property

from arq import ArqRedis
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.case_commands import CaseCommandHandler
from src.application.commands.data_commands import DataCommandHandler
from src.application.commands.schedule_commands import ScheduleCommandHandler
from src.application.interfaces.advisor_metrics_query_service import (
    AdvisorMetricsQueryService,
)
from src.application.interfaces.availability_query_service import (
    AdvisorAvailabilityQueryService,
)
from src.application.interfaces.background_queue import BackgroundTaskQueue
from src.application.interfaces.case_query_service import CaseQueryService
from src.application.interfaces.gamification_query_service import (
    GamificationQueryService,
)
from src.application.interfaces.ledger_query_service import PointLedgerQueryService
from src.application.interfaces.pii_masker import PiiMasker
from src.application.interfaces.student_query_service import StudentQueryService
from src.application.queries.advisor_queries import AdvisorQueryHandler
from src.application.queries.case_queries import CaseQueryHandler
from src.application.queries.metrics_queries import MetricsQueryHandler
from src.application.queries.student_queries import StudentQueryHandler
from src.application.services.event_publisher import TaskQueueEventPublisher
from src.application.services.websocket_publisher import WebSocketEventPublisher
from src.core.config import config
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
from src.domain.repositories.schedule_repository import ScheduleRepository
from src.domain.repositories.settings_repository import UserSettingsRepository
from src.domain.repositories.status_history_repository import StatusHistoryRepository
from src.domain.repositories.student_repository import StudentRepository
from src.domain.services.anomaly_engine.anomaly_engine import AnomalyEngine
from src.domain.services.anomaly_engine.zscore import ZScore
from src.domain.services.availability import AdvisorAvailabilityService
from src.domain.services.email_drafting import EmailDraftingService
from src.domain.services.email_sending import EmailSendingService
from src.domain.services.gamification import GamificationService
from src.infrastructure.extern.email_sender import AioSmtpEmailSender
from src.infrastructure.extern.guardrails_drafting_service import (
    GuardrailsEmailDraftingService,
)
from src.infrastructure.extern.presidio_pii_masker import PresidioPiiMasker
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
from src.infrastructure.persistence.query_services.sqlalchemy_availability_query_service import (
    SqlAlchemyAdvisorAvailabilityQueryService,
)
from src.infrastructure.persistence.query_services.student_query_service import (
    SqlAlchemyStudentQueryService,
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
    SqlAlchemyScheduleRepository,
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
    ) -> None:
        """Initialize the container with core resources."""
        self.session = session
        self.redis_pool = redis_pool

    # Repositories
    @cached_property
    def student_repo(self) -> StudentRepository:
        """Student repository."""
        return SqlAlchemyStudentRepository(self.session)

    @cached_property
    def advisor_repo(self) -> AdvisorRepository:
        """Advisor repository."""
        return SqlAlchemyAdvisorRepository(self.session)

    @cached_property
    def idempotency_repo(self) -> IdempotencyRepository:
        """Idempotency repository."""
        return SqlAlchemyIdempotencyRepository(self.session)

    @cached_property
    def email_repo(self) -> EmailRepository:
        """Email repository."""
        return SqlAlchemyEmailRepository(self.session)

    @cached_property
    def case_repo(self) -> CaseRepository:
        """Case repository."""
        return SqlAlchemyCaseRepository(self.session)

    @cached_property
    def activity_repo(self) -> ActivityRepository:
        """Activity repository."""
        return SqlAlchemyActivityRepository(self.session)

    @cached_property
    def status_history_repo(self) -> StatusHistoryRepository:
        """Status history repository."""
        return SqlAlchemyStatusHistoryRepository(self.session)

    @cached_property
    def metrics_repo(self) -> MetricsRepository:
        """Metrics repository."""
        return SqlAlchemyMetricsRepository(self.session)

    @cached_property
    def metadata_repo(self) -> MetadataRepository:
        """Metadata repository."""
        return SqlAlchemyMetadataRepository(self.session)

    @cached_property
    def job_repo(self) -> JobRepository:
        """Job repository."""
        return SqlAlchemyJobRepository(self.session)

    @cached_property
    def user_settings_repo(self) -> UserSettingsRepository:
        """User settings repository."""
        return SqlAlchemyUserSettingsRepository(self.session)

    @cached_property
    def point_ledger_repo(self) -> PointLedgerRepository:
        """Point ledger repository."""
        return SqlAlchemyPointLedgerRepository(self.session)

    @cached_property
    def schedule_repo(self) -> ScheduleRepository:
        """Schedule repository."""
        return SqlAlchemyScheduleRepository(self.session)

    @cached_property
    def badge_repo(self) -> BadgeRepository:
        """Badge repository."""
        return SqlAlchemyBadgeRepository(self.session)

    # Services & Infrastructure
    @cached_property
    def gamification_service(self) -> GamificationService:
        """Gamification domain service."""
        return GamificationService()

    @cached_property
    def availability_service(self) -> AdvisorAvailabilityService:
        """Advisor availability service."""
        return AdvisorAvailabilityService(
            schedule_repo=self.schedule_repo,
            case_repo=self.case_repo,
        )

    @cached_property
    def email_sending_service(self) -> EmailSendingService:
        """Email sending infrastructure service."""
        return AioSmtpEmailSender(
            host=config.smtp_host,
            port=config.smtp_port,
            user=config.smtp_user,
            password=config.smtp_password,
            from_email=config.smtp_from_email,
        )

    @cached_property
    def anomaly_engine(self) -> AnomalyEngine:
        """Anomaly detection engine."""
        return ZScore()

    @cached_property
    def pii_masker(self) -> PiiMasker:
        """PII masking service."""
        return PresidioPiiMasker()

    @cached_property
    def email_drafting_service(self) -> EmailDraftingService:
        """Email drafting domain service."""
        return GuardrailsEmailDraftingService(pii_masker=self.pii_masker)

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
        """Domain event publisher."""
        return TaskQueueEventPublisher(self.task_queue)

    @cached_property
    def websocket_publisher(self) -> WebSocketEventPublisher:
        """WebSocket event publisher."""
        if self.redis_pool is None:
            raise ValueError('Redis pool is required for WebSocket publishing.')
        return WebSocketEventPublisher(self.redis_pool)

    # Query Services
    @cached_property
    def point_ledger_query_service(self) -> PointLedgerQueryService:
        """Point ledger query service."""
        return SqlAlchemyPointLedgerQueryService(self.session)

    @cached_property
    def availability_query_service(self) -> AdvisorAvailabilityQueryService:
        """Advisor availability query service."""
        return SqlAlchemyAdvisorAvailabilityQueryService(self.session)

    @cached_property
    def gamification_query_service(self) -> GamificationQueryService:
        """Gamification query service."""
        return SqlAlchemyGamificationQueryService(session=self.session)

    @cached_property
    def advisor_metrics_query_service(self) -> AdvisorMetricsQueryService:
        """Advisor metrics query service."""
        return SqlAlchemyAdvisorMetricsQueryService(session=self.session)

    @cached_property
    def case_query_service(self) -> CaseQueryService:
        """Case query service."""
        return SqlAlchemyCaseQueryService(
            session=self.session,
            gamification_service=self.gamification_service,
        )

    @cached_property
    def student_query_service(self) -> StudentQueryService:
        """Student query service."""
        return SqlAlchemyStudentQueryService(self.session)

    # Command Handlers
    def get_case_command_handler(self) -> CaseCommandHandler:
        """Case command handler."""
        return CaseCommandHandler(
            self.student_repo,
            self.email_repo,
            self.case_repo,
            self.advisor_repo,
            self.job_repo,
            self.task_queue,
            self.event_publisher,
            self.websocket_publisher,
            availability_service=self.availability_service,
            email_drafting_service=self.email_drafting_service,
        )

    def get_schedule_command_handler(self) -> ScheduleCommandHandler:
        """Schedule command handler."""
        return ScheduleCommandHandler(self.schedule_repo)

    def get_data_command_handler(self) -> DataCommandHandler:
        """Data command handler."""
        return DataCommandHandler(
            self.student_repo,
            self.activity_repo,
            self.status_history_repo,
            self.case_repo,
            self.job_repo,
            self.anomaly_engine,
            self.task_queue,
        )

    # Query Handlers
    def get_advisor_query_handler(self) -> AdvisorQueryHandler:
        """Advisor query handler."""
        return AdvisorQueryHandler(
            advisor_repo=self.advisor_repo,
            point_ledger_query_service=self.point_ledger_query_service,
            gamification_query_service=self.gamification_query_service,
            advisor_metrics_query_service=self.advisor_metrics_query_service,
            availability_query_service=self.availability_query_service,
        )

    def get_case_query_handler(self) -> CaseQueryHandler:
        """Case query handler."""
        return CaseQueryHandler(
            case_query_service=self.case_query_service,
            advisor_repo=self.advisor_repo,
            case_repo=self.case_repo,
            email_repo=self.email_repo,
            student_repo=self.student_repo,
        )

    def get_metrics_query_handler(self) -> MetricsQueryHandler:
        """Metrics query handler."""
        return MetricsQueryHandler(self.metrics_repo)

    def get_student_query_handler(self) -> StudentQueryHandler:
        """Student query handler."""
        return StudentQueryHandler(self.student_query_service)
