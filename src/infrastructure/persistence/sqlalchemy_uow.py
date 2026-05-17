"""SQLAlchemy implementation of the Unit of Work pattern."""

import pickle
import uuid
from typing import TYPE_CHECKING, Any, Self

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.unit_of_work import UnitOfWork
from src.core.identifiers import generate_uuid
from src.domain.entities.base import AggregateRoot
from src.domain.value_objects.status import OutboxStatus
from src.infrastructure.database.models import OutboxEvent
from src.infrastructure.persistence.repositories.sqlalchemy_repositories import (
    SqlAlchemyActivityRepository,
    SqlAlchemyAdvisorRepository,
    SqlAlchemyBadgeRepository,
    SqlAlchemyCaseRepository,
    SqlAlchemyEmailRepository,
    SqlAlchemyIdempotencyRepository,
    SqlAlchemyJobRepository,
    SqlAlchemyNotificationRepository,
    SqlAlchemyPointLedgerRepository,
    SqlAlchemyScheduleRepository,
    SqlAlchemyStatusHistoryRepository,
    SqlAlchemyStudentRepository,
    SqlAlchemyUserSettingsRepository,
)
from src.infrastructure.queue.outbox_mapper import OutboxMapper

if TYPE_CHECKING:
    from src.domain.events.base import DomainEvent


class SqlAlchemyUnitOfWork(UnitOfWork):
    """SQLAlchemy implementation of Unit of Work.

    Manages the lifecycle of a database transaction and ensures that
    domain events are persisted as outbox events atomically.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a SQLAlchemy session."""
        self.session = session
        self._entities: dict[int, AggregateRoot] = {}

        # Initialize repositories with event collection callback
        self.students = SqlAlchemyStudentRepository(
            self.session,
            collect_events_callback=self.collect_events,
        )
        self.emails = SqlAlchemyEmailRepository(
            self.session,
            collect_events_callback=self.collect_events,
        )
        self.cases = SqlAlchemyCaseRepository(
            self.session,
            collect_events_callback=self.collect_events,
        )
        self.advisors = SqlAlchemyAdvisorRepository(
            self.session,
            collect_events_callback=self.collect_events,
        )
        self.jobs = SqlAlchemyJobRepository(
            self.session,
            collect_events_callback=self.collect_events,
        )
        self.activities = SqlAlchemyActivityRepository(self.session)
        self.history = SqlAlchemyStatusHistoryRepository(self.session)
        self.schedules = SqlAlchemyScheduleRepository(self.session)
        self.badges = SqlAlchemyBadgeRepository(self.session)
        self.idempotency = SqlAlchemyIdempotencyRepository(self.session)
        self.user_settings = SqlAlchemyUserSettingsRepository(self.session)
        self.point_ledger = SqlAlchemyPointLedgerRepository(self.session)
        self.notification = SqlAlchemyNotificationRepository(
            self.session,
            collect_events_callback=self.collect_events,
        )

    async def __aenter__(self) -> Self:
        """Begin the unit of work."""
        return self

    async def __aexit__(
        self,
        exc_type: type | None,
        exc_val: Exception | None,
        exc_tb: Any,
    ) -> None:
        """Exit the unit of work, rolling back on error."""
        if exc_type:
            await self.rollback()
        # Note: We don't auto-commit here to give the caller control
        # and follow the Protocol's expectation of explicit commit.

    def collect_events(self, entity: AggregateRoot) -> None:
        """Register an entity to have its events collected on commit."""
        self._entities[id(entity)] = entity

    async def commit(self) -> None:
        """Commit changes and persist outbox events."""
        # 1. Collect all events from tracked entities
        all_events: list[DomainEvent] = []
        for entity in self._entities.values():
            all_events.extend(entity.domain_events)
            entity.clear_events()

        # 2. Map domain events to outbox records
        for event in all_events:
            tasks = OutboxMapper.map_to_tasks(event)
            for task in tasks:
                outbox_entry = OutboxEvent(
                    id=generate_uuid(),
                    task_name=task['task_name'],
                    payload=pickle.dumps(task['kwargs']),
                    status=OutboxStatus.PENDING,
                )
                self.session.add(outbox_entry)

        # 3. Final atomic commit
        await self.session.commit()
        self._entities.clear()

    async def rollback(self) -> None:
        """Roll back the current transaction."""
        await self.session.rollback()
        self._entities.clear()

    async def enqueue(self, task_name: str, **kwargs: Any) -> uuid.UUID:
        """Enqueue a task to the outbox."""
        event_id = generate_uuid()
        outbox_entry = OutboxEvent(
            id=event_id,
            task_name=task_name,
            payload=pickle.dumps(kwargs),
            status=OutboxStatus.PENDING,
        )
        self.session.add(outbox_entry)
        return event_id
