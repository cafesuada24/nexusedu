"""Repository interfaces for the domain."""

from src.domain.repositories.activity_repository import ActivityRepository
from src.domain.repositories.advisor_repository import AdvisorRepository
from src.domain.repositories.alert_repository import AlertRepository
from src.domain.repositories.email_repository import EmailRepository
from src.domain.repositories.idempotency_repository import IdempotencyRepository
from src.domain.repositories.metadata_repository import MetadataRepository
from src.domain.repositories.metrics_repository import MetricsRepository
from src.domain.repositories.status_history_repository import StatusHistoryRepository
from src.domain.repositories.student_repository import StudentRepository

__all__ = [
    'ActivityRepository',
    'AdvisorRepository',
    'AlertRepository',
    'EmailRepository',
    'IdempotencyRepository',
    'MetadataRepository',
    'MetricsRepository',
    'StatusHistoryRepository',
    'StudentRepository',
]
