"""Service layer for data ingestion and management."""

from typing import TYPE_CHECKING, Any

from src.api.models.request import CoreDataSource, DataIngestionRequest

if TYPE_CHECKING:
    from src.database.interfaces import AnomalyAlgorithm, DatabaseEngine
    from src.database.manager import DatabaseManager


class DataService:
    """Service for handling data ingestion and processing."""

    def __init__(self, db_manager: 'DatabaseManager[DatabaseEngine, AnomalyAlgorithm]') -> None:
        """Initialize the DataService.

        Args:
            db_manager: The database manager instance.
        """
        self.db = db_manager

    def ingest_data(self, request: DataIngestionRequest) -> dict[str, Any]:
        """Ingest multi-source data and trigger the anomaly engine.

        Args:
            request: The ingestion request containing data sources.

        Returns:
            A dictionary containing processing results and new at-risk SIDs.
        """
        results: list[str] = []

        for source in request.data_sources:
            if isinstance(source, CoreDataSource):
                db_id = f'{source.source_type}_db'
                table_name = 'students' if source.source_type == 'sis' else 'activities'

                # model_dump(by_alias=True) ensures we use 'sid' etc.
                records = [r.model_dump(by_alias=True) for r in source.records]

                self.db.ingest_records(db_id, table_name, records)
                results.append(
                    f'Ingested {len(records)} records into {db_id}.{table_name}',
                )
            else:  # Custom data source
                self.db.ingest_custom_data(source.table_name, source.records)
                results.append(
                    f'Ingested {len(source.records)} records into sis_db.{source.table_name}',
                )

        # Trigger Anomaly Detection Engine
        new_sids = self.db.run_anomaly_engine()
        results.append('Anomaly engine execution completed successfully.')

        return {
            'results': results,
            'new_sids': new_sids
        }
