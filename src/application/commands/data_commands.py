"""Command handlers for data-related operations."""

from collections import defaultdict
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from src.application.commands.case_commands import CaseCommandHandler
from src.application.dtos.data_dtos import DataIngestionCommand
from src.core.logger import logger
from src.domain.entities.case import Case
from src.domain.repositories.activity_repository import ActivityRepository
from src.domain.repositories.case_repository import CaseRepository
from src.domain.repositories.job_repository import JobRepository
from src.domain.repositories.status_history_repository import StatusHistoryRepository
from src.domain.repositories.student_repository import StudentRepository
from src.domain.services.anomaly_engine.anomaly_engine import AnomalyEngine
from src.domain.value_objects.status import InterventionStatus, RiskStatus


class DataCommandHandler:
    """Handler for data-related commands."""

    def __init__(
        self,
        student_repo: StudentRepository,
        activity_repo: ActivityRepository,
        history_repo: StatusHistoryRepository,
        case_repo: CaseRepository,
        job_repo: JobRepository,
        anomaly_engine: AnomalyEngine,
        case_command_handler: CaseCommandHandler,
    ):
        self.student_repo = student_repo
        self.activity_repo = activity_repo
        self.history_repo = history_repo
        self.case_repo = case_repo
        self.job_repo = job_repo
        self.anomaly_engine = anomaly_engine
        self.case_command_handler = case_command_handler

    async def handle_ingest_data(self, command: DataIngestionCommand) -> Mapping[str, Any]:
        """Execute the data ingestion command with orchestration."""
        results: list[str] = []

        for source in command.data_sources:
            if source.source_type == 'sis':
                await self.student_repo.ingest_students(source.records)
                results.append(f'Ingested {len(source.records)} student records.')
            elif source.source_type == 'lms':
                await self.activity_repo.ingest_activities(source.records)
                results.append(f'Ingested {len(source.records)} activity records.')

        # Orchestrate Anomaly Detection
        new_sids = await self._run_anomaly_detection()
        results.append(
            f'Anomaly engine execution completed. Found {len(new_sids)} new transitions.',
        )

        # Trigger automatic draft generation for new at-risk students
        triggered_jobs: list[dict[str, Any]] = []
        db_updates: list[tuple[UUID, str, UUID | None, str | None]] = []

        if db_updates:
            await self.job_repo.batch_create_jobs(db_updates)

        return {
            'results': results,
            'new_sids': new_sids,
            'triggered_jobs': triggered_jobs,
        }

    async def _run_anomaly_detection(self) -> list[tuple[UUID, UUID]]:
        """Orchestrate the anomaly detection process."""
        # 1. Fetch data
        weekly_avgs = await self.activity_repo.get_weekly_averages()
        existing_history = await self.history_repo.get_all_history()

        # 2. Prepare data for the pure domain service
        history_set = {
            (h['sid'], h['academic_year'], h['semester'], h['week'])
            for h in existing_history
        }

        student_data: dict[UUID, list[dict[str, Any]]] = defaultdict(list)
        for avg in weekly_avgs:
            student_data[avg['sid']].append(avg)

        # 3. Call the pure domain service
        new_history_records, risk_statuses = self.anomaly_engine.run(
            student_data,
            history_set,
        )

        # 4. Persist new history records
        if new_history_records:
            await self.history_repo.batch_create_history(new_history_records)

        # 5. Transition student statuses and identify new at-risk students
        new_at_risk_sids: list[tuple[UUID, UUID]] = []
        for sid, latest_risk in risk_statuses.items():
            student = await self.student_repo.get_by_id(sid)
            if not student:
                continue

            # Always update student risk status
            student.update_risk(latest_risk)
            await self.student_repo.save(student)

            if latest_risk == RiskStatus.NORMAL:
                continue

            active_case = await self.case_repo.get_active_case(sid)

            if active_case is None:
                # Create a new Case for this student if they don't have an active one

                new_case = Case(sid=sid, intervention_status=InterventionStatus.NEW)
                await self.case_repo.add(new_case)
                case_id = new_case.case_id
            else:
                case_id = active_case.case_id

            new_at_risk_sids.append((sid, case_id))

        return new_at_risk_sids
