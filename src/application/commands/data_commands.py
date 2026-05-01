"""Command handlers for data-related operations."""

from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from pydantic import UUID4

from src.application.commands.alert_commands import (
    AlertCommandHandler,
    TriggerDraftCommand,
)
from src.application.dtos.data_dtos import DataIngestionCommand
from src.domain.repositories.activity_repository import ActivityRepository
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
        anomaly_engine: AnomalyEngine,
        alert_command_handler: AlertCommandHandler,
    ):
        self.student_repo = student_repo
        self.activity_repo = activity_repo
        self.history_repo = history_repo
        self.anomaly_engine = anomaly_engine
        self.alert_command_handler = alert_command_handler

    async def handle_ingest_data(
        self,
        command: DataIngestionCommand,
        user_id: UUID4,
    ) -> Mapping[str, Any]:
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
            f'Anomaly engine execution completed. Found {len(new_sids)} new transitions.'
        )

        # Trigger automatic draft generation for new at-risk students
        triggered_jobs: list[dict[str, Any]] = []
        db_updates: list[tuple[UUID4, UUID4]] = []

        for sid in new_sids:
            trigger_command = TriggerDraftCommand(
                sid=sid,
                user_id=user_id,
                update_db=False,
            )
            job_id = await self.alert_command_handler.handle_trigger_draft(
                trigger_command
            )
            triggered_jobs.append({'sid': sid, 'job_id': job_id})
            db_updates.append((job_id, sid))

        # Batch update draft_job_id
        if db_updates:
            await self.student_repo.batch_update_draft_job_ids(db_updates)

        return {
            'results': results,
            'new_sids': new_sids,
            'triggered_jobs': triggered_jobs,
        }

    async def _run_anomaly_detection(self) -> list[UUID4]:
        """Orchestrate the anomaly detection process."""
        # 1. Fetch data
        weekly_avgs = await self.activity_repo.get_weekly_averages()
        existing_history = await self.history_repo.get_all_history()

        # 2. Prepare data for the pure domain service
        history_set = {
            (h['sid'], h['academic_year'], h['semester'], h['week'])
            for h in existing_history
        }

        student_data: dict[UUID4, list[dict[str, Any]]] = defaultdict(list)
        for avg in weekly_avgs:
            student_data[avg['sid']].append(avg)

        # 3. Call the pure domain service
        new_history_records, risk_statuses = self.anomaly_engine.run(
            student_data, history_set
        )

        # 4. Persist new history records
        if new_history_records:
            await self.history_repo.batch_create_history(new_history_records)

        # 5. Transition student statuses and identify new at-risk students
        new_at_risk_sids: list[UUID4] = []
        for sid, latest_risk in risk_statuses.items():
            if latest_risk == RiskStatus.NORMAL:
                continue

            student = await self.student_repo.get_by_id(sid)
            if not student:
                continue

            if student.intervention_status in (
                InterventionStatus.NONE,
                InterventionStatus.RESOLVED,
            ):
                await self.student_repo.update_risk_status(
                    sid,
                    risk_status=latest_risk,
                    intervention_status=InterventionStatus.NOTIFIED,
                )
                new_at_risk_sids.append(sid)
            else:
                await self.student_repo.update_risk_status(sid, risk_status=latest_risk)

        return new_at_risk_sids
