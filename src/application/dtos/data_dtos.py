"""Data Transfer Objects for data-related operations."""

from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class DataSourceDTO:
    """DTO for a single data source in an ingestion request."""

    source_type: Literal['sis', 'lms']
    records: list[dict[str, Any]]


@dataclass
class DataIngestionCommand:
    """Command to ingest data from multiple sources."""

    data_sources: list[DataSourceDTO]
