"""API routes for data ingestion and management."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from src.api.auth import Scope, User, require_scope
from src.api.lifecycle import get_alert_service, get_data_service, get_jobs_store
from src.api.models.request import DataIngestionRequest
from src.api.services.alerts import AlertService
from src.api.services.data import DataService
from src.api.types import JobStore
from src.telemetry.logger import logger

router = APIRouter(prefix='/data', tags=['data'])


@router.post('/ingest')
async def ingest_data(
    request: DataIngestionRequest,
    background_tasks: BackgroundTasks,
    data_service: Annotated[DataService, Depends(get_data_service)],
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
    jobs: Annotated[JobStore, Depends(get_jobs_store)],
    user: Annotated[User, Depends(require_scope(Scope.DATA_INGEST))],
) -> dict[str, object]:
    """Ingest multi-source data from JSON payload.

    Supports validated 'sis' and 'lms' sources, plus flexible 'custom' sources.
    Automatically triggers the anomaly detection engine post-ingestion.
    For students transitioning to 'new' risk status, triggers AI draft generation.

    Args:
        request: The structured data ingestion request.
        background_tasks: FastAPI background tasks.
        data_service: The data service instance.
        alert_service: The alert service instance for triggering drafts.
        jobs: The job store dependency.
        user: The authenticated admin user.

    Returns:
        Summary of ingestion results.
    """
    try:
        results = data_service.ingest_data(request)
        new_sids = results.get('new_sids', [])

        # Trigger automatic draft generation for new at-risk students
        triggered_jobs = []
        db_updates = []
        for sid in new_sids:
            job_id = alert_service.trigger_draft(
                sid=sid,
                background_tasks=background_tasks,
                jobs=jobs,
                user_id=str(user.id),
                update_db=False,  # We will batch update instead
            )
            triggered_jobs.append({'sid': sid, 'job_id': job_id})
            db_updates.append((job_id, sid))

        # Batch update draft_job_id to avoid blocking and improve performance
        if db_updates:
            data_service.db.update_draft_job_ids(db_updates)

        return {
            'status': 'success',
            'batch_id': request.batch_id,
            'results': results['results'],
            'automatic_drafts': triggered_jobs,
        }

    except Exception as e:
        logger.error(f'Critical error during data ingestion: {e}', exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
