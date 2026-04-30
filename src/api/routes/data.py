"""API routes for data ingestion and management."""

from typing import Annotated, Any

from arq import ArqRedis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import Scope, User, require_scope
from src.api.lifecycle import (
    get_alert_service,
    get_arq_pool,
    get_data_service,
    get_jobs_store,
)
from src.api.models.request import DataIngestionRequest
from src.api.services.alerts import AlertService
from src.api.services.data import DataService
from src.api.types import JobStore
from src.database.session import get_async_session
from src.telemetry.logger import logger

router = APIRouter(prefix='/data', tags=['data'])


@router.post('/ingest')
async def ingest_data(
    request: DataIngestionRequest,
    arq_pool: Annotated[ArqRedis | None, Depends(get_arq_pool)],
    data_service: Annotated[DataService, Depends(get_data_service)],
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
    jobs: Annotated[JobStore, Depends(get_jobs_store)],
    user: Annotated[User, Depends(require_scope(Scope.DATA_INGEST))],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> dict[str, object]:
    """Ingest multi-source data from JSON payload.

    Supports validated 'sis' and 'lms' sources, plus flexible 'custom' sources.
    Automatically triggers the anomaly detection engine post-ingestion.
    For students transitioning to 'new' risk status, triggers AI draft generation.
    """
    try:
        async with session.begin():
            results = await data_service.ingest_data(request)
            new_sids = results.get('new_sids', [])

            # Trigger automatic draft generation for new at-risk students
            triggered_jobs: list[dict[str, int | str]] = []
            db_updates: list[tuple[str, str]] = []
            for sid in new_sids:
                job_id = await alert_service.trigger_draft(
                    sid=sid,
                    arq_pool=arq_pool,
                    jobs=jobs,
                    user_id=str(user.id),
                    update_db=False,  # We will batch update instead
                )
                triggered_jobs.append({'sid': sid, 'job_id': job_id})
                db_updates.append((job_id, sid))

            # Batch update draft_job_id
            if db_updates:
                await data_service.batch_update_draft_job_ids(db_updates)

        return {
            'status': 'success',
            'batch_id': request.batch_id,
            'results': results['results'],
            'automatic_drafts': triggered_jobs,
        }

    except Exception as e:
        logger.error(f'Critical error during data ingestion: {e}', exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
