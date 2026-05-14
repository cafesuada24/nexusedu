"""Interface for the Unit of Work pattern."""

import uuid
from typing import Any, Protocol, Self

from src.domain.repositories.activity_repository import ActivityRepository
from src.domain.repositories.advisor_repository import AdvisorRepository
from src.domain.repositories.badge_repository import BadgeRepository
from src.domain.repositories.case_repository import CaseRepository
from src.domain.repositories.email_repository import EmailRepository
from src.domain.repositories.idempotency_repository import IdempotencyRepository
from src.domain.repositories.job_repository import JobRepository
from src.domain.repositories.point_ledger_repository import PointLedgerRepository
from src.domain.repositories.schedule_repository import ScheduleRepository
from src.domain.repositories.settings_repository import UserSettingsRepository
from src.domain.repositories.status_history_repository import StatusHistoryRepository
from src.domain.repositories.student_repository import StudentRepository


class UnitOfWork(Protocol):
    """Interface for managing atomic transactions across multiple repositories."""

    students: StudentRepository
    emails: EmailRepository
    cases: CaseRepository
    advisors: AdvisorRepository
    jobs: JobRepository
    activities: ActivityRepository
    history: StatusHistoryRepository
    schedules: ScheduleRepository
    badges: BadgeRepository
    idempotency: IdempotencyRepository
    user_settings: UserSettingsRepository
    point_ledger: PointLedgerRepository

    async def __aenter__(self) -> Self:
        """Begin a transaction."""
        ...

    async def __aexit__(
        self,
        exc_type: type | None,
        exc_val: Exception | None,
        exc_tb: Any,
    ) -> None:
        """End a transaction, rolling back if an exception occurred."""
        ...

    async def commit(self) -> None:
        """Commit the current transaction and extract/persist domain events."""
        ...

    async def rollback(self) -> None:
        """Roll back the current transaction."""
        ...

    async def enqueue(
        self,
        task_name: str,
        **kwargs: Any,
    ) -> uuid.UUID:
        """Enqueue a background task atomically with the transaction."""
        ...
