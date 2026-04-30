"""Service layer for data ingestion and management."""

from typing import Any

from src.domain.repositories.interfaces import ActivityRepository, StudentRepository
from src.domain.services.anomaly_engine import AnomalyEngine
from src.presentation.schemas.request import CoreDataSource, DataIngestionRequest


class DataService:
    """Service for handling data ingestion and processing."""

    def __init__(
        self,
        student_repo: StudentRepository,
        activity_repo: ActivityRepository,
        anomaly_engine: AnomalyEngine,
    ) -> None:
        """Initialize the DataService.

        Args:
            student_repo: Repository for student operations.
            activity_repo: Repository for activity operations.
            anomaly_engine: Service for anomaly detection.
        """
        self.student_repo = student_repo
        self.activity_repo = activity_repo
        self.anomaly_engine = anomaly_engine

    async def ingest_data(self, request: DataIngestionRequest) -> dict[str, Any]:
        """Ingest multi-source data and trigger the anomaly engine.

        Args:
            request: The ingestion request containing data sources.

        Returns:
            A dictionary containing processing results and new at-risk SIDs.
        """
        results: list[str] = []

        for source in request.data_sources:
            if isinstance(source, CoreDataSource):
                # model_dump(by_alias=True) ensures we use 'sid' etc.
                records = [r.model_dump(by_alias=True) for r in source.records]

                if source.source_type == 'sis':
                    await self.student_repo.ingest_students(records)
                    results.append(f'Ingested {len(records)} student records.')
                else:
                    await self.activity_repo.ingest_activities(records)
                    results.append(f'Ingested {len(records)} activity records.')
            else:  # Custom data source
                # For custom data, we'll need a way to handle dynamic tables in SQLAlchemy
                # For now, let's log that it's not yet supported in the refactored version
                # or implement a generic dynamic table handler.
                results.append(
                    f'Custom table {source.table_name} ingestion skipped (Refactoring in progress).',
                )

        # Trigger Anomaly Detection Engine
        new_sids = await self.anomaly_engine.run()
        results.append('Anomaly engine execution completed successfully.')

        return {
            'results': results,
            'new_sids': new_sids,
        }

    async def batch_update_draft_job_ids(self, updates: list[tuple[str, str]]) -> None:
        """Batch update draft job IDs for multiple students."""
        await self.student_repo.batch_update_draft_job_ids(updates)
