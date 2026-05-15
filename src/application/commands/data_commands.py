"""Command handlers for data-related operations."""

from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from src.application.dtos.data_dtos import DataIngestionCommand
from src.application.interfaces.unit_of_work import UnitOfWork
from src.core.identifiers import EntityID, generate_uuid
from src.domain.entities.case import Case
from src.domain.entities.data_ingestion import DataIngestion
from src.domain.events.data_events import DataIngestedEvent
from src.domain.services.anomaly_engine.anomaly_engine import AnomalyEngine
from src.domain.value_objects.status import InterventionStatus, RiskStatus


class DataCommandHandler:
    """Handler for data-related operations."""

    def __init__(
        self,
        uow: UnitOfWork,
        anomaly_engine: AnomalyEngine,
    ) -> None:
        """Initialize the data command handler."""
        self.uow = uow
        self.anomaly_engine = anomaly_engine

    async def handle_ingest_data(
        self,
        command: DataIngestionCommand,
        job_id: EntityID | None = None,
    ) -> Mapping[str, Any]:
        """Execute the data ingestion command with orchestration."""
        results: list[str] = []
        async with self.uow:
            for source in command.data_sources:
                if source.source_type == 'sis':
                    await self.uow.students.ingest_students(source.records)
                    results.append(f'Ingested {len(source.records)} student records.')
                elif source.source_type == 'lms':
                    await self.uow.activities.ingest_activities(source.records)
                    results.append(f'Ingested {len(source.records)} activity records.')

            await self.uow.commit()

            # Orchestrate Anomaly Detection
            new_sids = await self._run_anomaly_detection()
            results.append(
                f'Anomaly engine execution completed. Found {len(new_sids)} new transitions.',
            )

            # Publish Ingestion Event
            ingestion = DataIngestion()
            ingestion.register_event(
                DataIngestedEvent(
                    job_id=job_id or generate_uuid(),
                    new_sids=new_sids,
                    results=results,
                ),
            )
            self.uow.collect_events(ingestion)
            await self.uow.commit()

            return {
                'results': results,
                'new_sids': new_sids,
            }

    async def _run_anomaly_detection(self) -> list[tuple[EntityID, EntityID]]:
        """Orchestrate the anomaly detection process."""
        # 1. Fetch data
        weekly_avgs = await self.uow.activities.get_weekly_averages()
        existing_history = await self.uow.history.get_all_history()

        # 2. Prepare data for the pure domain service
        history_set = {
            (h['sid'], h['academic_year'], h['semester'], h['week'])
            for h in existing_history
        }

        student_data: dict[EntityID, list[dict[str, Any]]] = defaultdict(list)
        for avg in weekly_avgs:
            student_data[avg['sid']].append(avg)

        # 3. Call the pure domain service
        new_history_records, risk_statuses = self.anomaly_engine.run(
            student_data,
            history_set,
        )

        # 4. Persist new history records
        if new_history_records:
            await self.uow.history.batch_create_history(new_history_records)

        # 5. Transition student statuses and identify new at-risk students
        new_at_risk_sids: list[tuple[EntityID, EntityID]] = []
        for sid, latest_risk in risk_statuses.items():
            student = await self.uow.students.get_by_id(sid)
            if not student:
                continue

            # Always update student risk status
            student.update_risk(latest_risk)
            await self.uow.students.save(student)

            if latest_risk == RiskStatus.NORMAL:
                continue

            active_case = await self.uow.cases.get_active_case(sid)

            if active_case is None:
                # Create a new Case for this student if they don't have an active one
                new_case = Case(sid=sid, intervention_status=InterventionStatus.NEW)
                await self.uow.cases.add(new_case)
                case_id = new_case.case_id
            else:
                case_id = active_case.case_id

            new_at_risk_sids.append((sid, case_id))

        if new_at_risk_sids:
            # Batch process AI overviews for new cases
            await self.uow.enqueue('run_batch_case_overviews_task')

        return new_at_risk_sids
