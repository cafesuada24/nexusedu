"""API routes for data ingestion and management."""

from typing import Annotated, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Header

from src.application.dtos.data_dtos import DataSourceDTO
from src.application.dtos.worker_payloads.data_payloads import DataIngestPayload
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.repositories.idempotency_repository import IdempotencyRepository
from src.presentation.api.auth import Scope, User, require_scope
from src.presentation.dependencies.providers import (
    get_idempotency_repository,
    get_unit_of_work,
)
from src.presentation.schemas.request import CoreDataSource, DataIngestionRequest

logger = structlog.get_logger(__name__)

router = APIRouter(prefix='/data', tags=['data'])


@router.post('/ingest')
async def ingest_data(
    request: DataIngestionRequest,
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    idempotency_repo: Annotated[IdempotencyRepository, Depends(get_idempotency_repository)],
    _: Annotated[User, Depends(require_scope(Scope.DATA_INGEST))],
    idempotency_key: Annotated[str | None, Header(alias='Idempotency-Key')] = None,
) -> dict[str, Any]:
    """Ingest multi-source data from JSON payload asynchronously.

    Supports validated 'sis' and 'lms' sources, plus flexible 'custom' sources.
    Enqueues a background task for ingestion and anomaly detection.
    """
    if idempotency_key:
        idemp_key = UUID(idempotency_key)
        if await idempotency_repo.check_key(idemp_key):
            logger.info('Idempotency hit for ingest_data', idemp_key=str(idemp_key))
            return {
                'status': 'success',
                'batch_id': request.batch_id,
                'message': 'Data already ingested (idempotent).',
            }

    # Map request to command DTO
    data_sources: list[DataSourceDTO] = []
    for source in request.data_sources:
        if isinstance(source, CoreDataSource):
            data_sources.append(
                DataSourceDTO(
                    source_type=source.source_type,
                    records=[r.model_dump(by_alias=True) for r in source.records],
                ),
            )

    async with uow:
        job_id = await uow.enqueue(
            'run_data_ingest_task',
            payload=DataIngestPayload(data_sources=data_sources),
        )

        if idempotency_key:
            await idempotency_repo.record_key(UUID(idempotency_key))

        await uow.commit()

    return {
        'status': 'success',
        'batch_id': request.batch_id,
        'job_id': str(job_id),
        'message': 'Data ingestion started in background.',
    }
