"""API routes for data ingestion and management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from src.api.auth import User, check_role
from src.api.lifecycle import get_dbmanager
from src.api.models.request import (
    CoreDataSource,
    DataIngestionRequest,
)
from src.database.manager import DatabaseManager
from src.telemetry.logger import logger

router = APIRouter(prefix='/data', tags=['data'])


@router.post('/ingest')
async def ingest_data(
    request: DataIngestionRequest,
    db_manager: Annotated[DatabaseManager, Depends(get_dbmanager)],
    user: Annotated[User, Depends(check_role('admin:all'))],
) -> dict[str, object]:
    """Ingest multi-source data from JSON payload.

    Supports validated 'sis' and 'lms' sources, plus flexible 'custom' sources.
    Automatically triggers the anomaly detection engine post-ingestion.

    Args:
        request: The structured data ingestion request.

    Returns:
        Summary of ingestion results.
    """
    results: list[str] = []

    try:
        for source in request.data_sources:
            if isinstance(source, CoreDataSource):
                db_id = f'{source.source_type}_db'
                # Table mapping based on core source type
                table_name = 'students' if source.source_type == 'sis' else 'activities'

                # model_dump(by_alias=True) ensures we use 'sid' etc. if aliases are set
                records = [r.model_dump(by_alias=True) for r in source.records]

                db_manager.ingest_records(db_id, table_name, records)
                results.append(
                    f'Ingested {len(records)} records into {db_id}.{table_name}',
                )
            else:  # Custom data source
                db_manager.ingest_custom_data(source.table_name, source.records)
                results.append(
                    f'Ingested {len(source.records)} records into sis_db.{source.table_name}',
                )

        # Trigger Anomaly Detection Engine
        db_manager.run_anomaly_engine()
        results.append('Anomaly engine execution completed successfully.')

        return {'status': 'success', 'batch_id': request.batch_id, 'results': results}

    except Exception as e:
        logger.error(f'Critical error during data ingestion: {e}', exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
