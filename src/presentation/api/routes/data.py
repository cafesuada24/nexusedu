"""API routes for data ingestion and management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.data_commands import DataCommandHandler
from src.application.dtos.data_dtos import DataIngestionCommand, DataSourceDTO
from src.infrastructure.database.session import get_async_session
from src.presentation.api.auth import Scope, User, require_scope
from src.presentation.dependencies.providers import (
    get_data_command_handler,
)
from src.presentation.schemas.request import CoreDataSource, DataIngestionRequest
from src.telemetry.logger import logger

router = APIRouter(prefix='/data', tags=['data'])


@router.post('/ingest')
async def ingest_data(
    request: DataIngestionRequest,
    command_handler: Annotated[DataCommandHandler, Depends(get_data_command_handler)],
    user: Annotated[User, Depends(require_scope(Scope.DATA_INGEST))],
    # session: Annotated[AsyncSession, Depends(get_async_session)],
) -> dict[str, object]:
    """Ingest multi-source data from JSON payload.

    Supports validated 'sis' and 'lms' sources, plus flexible 'custom' sources.
    Automatically triggers the anomaly detection engine post-ingestion.
    For students transitioning to 'new' risk status, triggers AI draft generation.
    """
    try:
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


        command = DataIngestionCommand(data_sources=data_sources)

        results = await command_handler.handle_ingest_data(command, user.id)

        return {
            'status': 'success',
            'batch_id': request.batch_id,
            'results': results['results'],
            'automatic_drafts': results.get('triggered_jobs', []),
        }

    except Exception as e:
        logger.error(f'Critical error during data ingestion: {e}', exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
