"""Worker payloads for data-related tasks."""

from src.application.dtos.data_dtos import DataSourceDTO
from src.application.dtos.worker_payloads.base import BaseWorkerPayload


class DataIngestPayload(BaseWorkerPayload):
    """Payload for background data ingestion."""

    data_sources: list[DataSourceDTO]
