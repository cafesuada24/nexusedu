"""Data ingestion process entity."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.core.identifiers import EntityID, generate_uuid
from src.domain.entities.base import AggregateRoot


@dataclass
class DataIngestion(AggregateRoot):
    """Data ingestion process."""

    ingestion_id: EntityID = field(default_factory=generate_uuid)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
