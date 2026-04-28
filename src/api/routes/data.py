"""API routes for data ingestion and management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from src.api.auth import User, check_role
from src.api.lifecycle import get_data_service
from src.api.models.request import (
    DataIngestionRequest,
)
from src.api.services.data import DataService
from src.telemetry.logger import logger

router = APIRouter(prefix='/data', tags=['data'])


@router.post('/ingest')
async def ingest_data(
    request: DataIngestionRequest,
    data_service: Annotated[DataService, Depends(get_data_service)],
    _user: Annotated[User, Depends(check_role('admin:all'))],
) -> dict[str, object]:
    """Ingest multi-source data from JSON payload.

    Supports validated 'sis' and 'lms' sources, plus flexible 'custom' sources.
    Automatically triggers the anomaly detection engine post-ingestion.

    Args:
        request: The structured data ingestion request.
        data_service: The data service instance.
        user: The authenticated admin user.

    Returns:
        Summary of ingestion results.
    """
    try:
        results = data_service.ingest_data(request)
        return {'status': 'success', 'batch_id': request.batch_id, 'results': results}

    except Exception as e:
        logger.error(f'Critical error during data ingestion: {e}', exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
