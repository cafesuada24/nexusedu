"""Z-Score anomaly detection algorithm implemented with pure domain logic."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import structlog

from src.core.identifiers import EntityID, generate_uuid
from src.domain.value_objects.status import RiskStatus

logger = structlog.get_logger(__name__)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from src.core.identifiers import EntityID


@dataclass
class ZScoreConfig:
    """ZScore algorithm config."""

    threshold: float = -1.5
    critical_drop_ratio: float = 0.7


class ZScore:
    """ZScore algorithm service for calculating academic performance anomalies."""

    def __init__(
        self,
        config: ZScoreConfig | None = None,
    ) -> None:
        """Initialize the ZScore service with configuration."""
        if config is None:
            config = ZScoreConfig()
        self.config = config

    def run(
        self,
        student_data: Mapping[EntityID, Sequence[Mapping[str, int | float]]],
        history_set: set[tuple[EntityID, int, int, int]],
    ) -> tuple[list[dict[str, Any]], dict[EntityID, RiskStatus]]:
        """Calculate anomalies and return results for orchestration.

        Returns:
            A tuple of (new_history_records, student_risk_statuses).
        """
        logger.info('ZScore: Starting calculation...')

        new_history_records, risk_statuses = self._calculate_anomalies(
            student_data,
            history_set,
        )

        logger.info(
            'ZScore: Calculation completed',
            anomaly_count=len(new_history_records),
        )
        return new_history_records, risk_statuses

    def _calculate_anomalies(
        self,
        student_data: Mapping[EntityID, Sequence[Mapping[str, int | float]]],
        history_set: set[tuple[EntityID, int, int, int]],
    ) -> tuple[list[dict[str, Any]], dict[EntityID, RiskStatus]]:
        """Identify new anomalies based on score trends."""
        new_records: list[dict[str, Any]] = []
        risk_statuses: dict[EntityID, RiskStatus] = {}

        for sid, weeks in student_data.items():
            sorted_weeks = sorted(
                weeks,
                key=lambda x: (x['academic_year'], x['semester'], x['week']),
            )

            historical_scores: list[float] = []
            latest_risk = RiskStatus.NORMAL

            for w in sorted_weeks:
                week_key = (sid, w['academic_year'], w['semester'], w['week'])

                if historical_scores:
                    record, week_risk = self._process_week(
                        sid,
                        w,
                        historical_scores,
                        week_key in history_set,
                    )
                    if record:
                        new_records.append(record)

                    # Update latest risk status for the student
                    latest_risk = week_risk

                historical_scores.append(w['avg_score'])

            risk_statuses[sid] = latest_risk

        return new_records, risk_statuses

    def _process_week(
        self,
        sid: EntityID,
        week_data: Mapping[str, int | float],
        historical_scores: list[float],
        exists: bool,
    ) -> tuple[dict[str, Any] | None, RiskStatus]:
        """Calculate metrics for a single week and return a record if it's new."""
        hs_cnt = len(historical_scores)
        baseline_avg = sum(historical_scores) / hs_cnt if hs_cnt > 0 else 0.0
        variance = (
            sum((x - baseline_avg) ** 2 for x in historical_scores) / hs_cnt
            if hs_cnt > 0
            else 0.0
        )
        baseline_std = math.sqrt(variance)

        current_avg = week_data['avg_score']
        z_score = (
            ((current_avg - baseline_avg) / baseline_std) if baseline_std > 0 else 0.0
        )

        if current_avg < baseline_avg * self.config.critical_drop_ratio:
            anomaly_flag = RiskStatus.CRITICAL
        elif z_score < self.config.threshold:
            anomaly_flag = RiskStatus.ELEVATED
        else:
            anomaly_flag = RiskStatus.NORMAL

        record = None
        if not exists:
            record = {
                'history_id': generate_uuid(),
                'sid': sid,
                'academic_year': week_data['academic_year'],
                'semester': week_data['semester'],
                'week': week_data['week'],
                'baseline_avg': baseline_avg,
                'baseline_std': baseline_std,
                'current_score_avg': current_avg,
                'z_score': z_score,
                'anomaly_flag': anomaly_flag.value,
            }

        return record, anomaly_flag
