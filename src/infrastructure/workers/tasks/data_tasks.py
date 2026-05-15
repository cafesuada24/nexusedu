"""Worker tasks for data ingestion."""

import structlog

from src.application.dtos.data_dtos import DataIngestionCommand
from src.application.dtos.worker_payloads.data_payloads import DataIngestPayload
from src.infrastructure.workers.framework.context import TaskContext
from src.infrastructure.workers.framework.decorators import worker_task

logger = structlog.get_logger(__name__)


@worker_task()
async def run_data_ingest_task(
    ctx: TaskContext,
    payload: DataIngestPayload,
) -> None:
    """Task to perform background data ingestion and anomaly detection."""
    logger.info(
        'running_data_ingest_task',
        job_id=str(ctx.job_tracker.job_id),
        data_source_count=len(payload.data_sources),
    )

    command = DataIngestionCommand(data_sources=payload.data_sources)
    handler = ctx.container.get_data_command_handler()

    # The TransactionMiddleware will handle the transaction lifecycle
    await handler.handle_ingest_data(command, job_id=ctx.job_tracker.job_id)

    logger.info(
        'data_ingest_task_completed',
        job_id=str(ctx.job_tracker.job_id),
    )
