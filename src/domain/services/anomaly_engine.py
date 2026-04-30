"""Z-Score anomaly detection algorithm implemented with SQLAlchemy repositories."""

from __future__ import annotations

import math
import uuid
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from src.telemetry.logger import logger

if TYPE_CHECKING:
    from src.domain.ports.repositories import (
        ActivityRepository,
        StatusHistoryRepository,
        StudentRepository,
    )

# Constants for anomaly detection thresholds
Z_SCORE_THRESHOLD = -1.5
CRITICAL_DROP_RATIO = 0.7


class AnomalyEngine:
    """Service for calculating academic performance anomalies using repositories."""

    def __init__(
        self,
        student_repo: StudentRepository,
        activity_repo: ActivityRepository,
        history_repo: StatusHistoryRepository,
    ) -> None:
        """Initialize the AnomalyEngine with repository ports."""
        self.student_repo = student_repo
        self.activity_repo = activity_repo
        self.history_repo = history_repo

    async def run(self) -> list[str]:
        """Calculate anomalies and update student risk statuses.

        Returns:
            List of student IDs whose status transitioned to 'new'.
        """
        logger.info('AnomalyEngine: Starting execution...')

        student_data, history_set = await self._fetch_and_group_data()

        new_history_records = self._calculate_new_history(student_data, history_set)

        if new_history_records:
            logger.info(
                f'AnomalyEngine: Persisting {len(new_history_records)} new history records.'
            )
            await self.history_repo.batch_create_history(new_history_records)

        new_at_risk_sids = await self._transition_student_statuses(
            list(student_data.keys())
        )

        logger.info(
            f'AnomalyEngine: Execution completed. Found {len(new_at_risk_sids)} new at-risk students.'
        )
        return new_at_risk_sids

    async def _fetch_and_group_data(
        self,
    ) -> tuple[dict[str, list[dict[str, Any]]], set[tuple[str, int, int, int]]]:
        """Fetch data from repositories and group by student."""
        weekly_avgs = await self.activity_repo.get_weekly_averages()
        existing_history = await self.history_repo.get_all_history()

        history_set = {
            (h['sid'], h['academic_year'], h['semester'], h['week'])
            for h in existing_history
        }

        student_data = defaultdict(list)
        for avg in weekly_avgs:
            student_data[avg['sid']].append(avg)

        return student_data, history_set

    def _calculate_new_history(
        self,
        student_data: dict[str, list[dict[str, Any]]],
        history_set: set[tuple[str, int, int, int]],
    ) -> list[dict[str, Any]]:
        """Identify new anomalies based on score trends."""
        new_records = []
        for sid, weeks in student_data.items():
            weeks.sort(key=lambda x: (x['academic_year'], x['semester'], x['week']))

            historical_scores: list[float] = []
            for w in weeks:
                week_key = (sid, w['academic_year'], w['semester'], w['week'])

                if historical_scores:
                    record = self._process_week(
                        sid, w, historical_scores, week_key in history_set
                    )
                    if record:
                        new_records.append(record)

                historical_scores.append(w['avg_score'])
        return new_records

    def _process_week(
        self,
        sid: str,
        week_data: dict[str, Any],
        historical_scores: list[float],
        exists: bool,
    ) -> dict[str, Any] | None:
        """Calculate metrics for a single week and return a record if it's new."""
        baseline_avg = sum(historical_scores) / len(historical_scores)
        variance = (
            sum((x - baseline_avg) ** 2 for x in historical_scores)
            / len(historical_scores)
        )
        baseline_std = math.sqrt(variance)

        current_avg = week_data['avg_score']
        z_score = (
            ((current_avg - baseline_avg) / baseline_std) if baseline_std > 0 else 0
        )

        if z_score < Z_SCORE_THRESHOLD:
            anomaly_flag = 'Significant Drop'
        elif current_avg < baseline_avg * CRITICAL_DROP_RATIO:
            anomaly_flag = 'Critical Drop'
        else:
            anomaly_flag = 'Normal'

        if not exists:
            return {
                'history_id': str(uuid.uuid4()),
                'sid': sid,
                'academic_year': week_data['academic_year'],
                'semester': week_data['semester'],
                'week': week_data['week'],
                'baseline_avg': baseline_avg,
                'baseline_std': baseline_std,
                'current_score_avg': current_avg,
                'z_score': z_score,
                'anomaly_flag': anomaly_flag,
            }
        return None

    async def _transition_student_statuses(self, sids: list[str]) -> list[str]:
        """Update risk status in the student registry and identify new transitions."""
        new_at_risk = []
        for sid in sids:
            latest_anomaly = await self.history_repo.get_latest_anomaly(sid)
            if not latest_anomaly or latest_anomaly == 'Normal':
                continue

            student = await self.student_repo.get_by_id(sid)
            if not student:
                continue

            if student.intervention_status in ('none', 'resolved', 'expired'):
                await self.student_repo.update_risk_status(
                    sid, risk_status=latest_anomaly, intervention_status='new'
                )
                new_at_risk.append(sid)
            else:
                await self.student_repo.update_risk_status(
                    sid, risk_status=latest_anomaly
                )
        return new_at_risk
