"""Base classes for domain entities."""

from dataclasses import dataclass, field

from src.domain.events.base import DomainEvent


@dataclass
class AggregateRoot:
    """Base class for aggregate roots with domain event support.

    Aggregate roots are responsible for maintaining consistency boundaries
    and can emit domain events when their state changes.
    """

    _domain_events: list[DomainEvent] = field(
        default_factory=list[DomainEvent],
        init=False,
        repr=False,
    )

    @property
    def domain_events(self) -> list[DomainEvent]:
        """Return a copy of registered domain events."""
        return list(self._domain_events)

    def clear_events(self) -> None:
        """Clear all registered domain events."""
        self._domain_events.clear()

    def register_event(self, event: DomainEvent) -> None:
        """Register a new domain event."""
        self._domain_events.append(event)
