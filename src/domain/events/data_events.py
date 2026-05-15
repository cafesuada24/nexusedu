"""Data-related domain events."""

from dataclasses import dataclass

from src.core.identifiers import EntityID
from src.domain.events.base import DomainEvent


@dataclass(frozen=True)
class DataIngestedEvent(DomainEvent):
    """Event triggered when data ingestion and anomaly detection are complete."""

    job_id: EntityID
    new_sids: list[tuple[EntityID, EntityID]]
    results: list[str]
