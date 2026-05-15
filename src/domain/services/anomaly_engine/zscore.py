"""Adaptive Evaluation Engine using Volatility-Aware Drift and Systemic Breadth."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import structlog

from src.core.identifiers import generate_uuid
from src.domain.services.anomaly_engine.domain_mapper import DomainMapper
from src.domain.services.anomaly_engine.models import (
    ActivityMeasurement,
    EvaluationResult,
    StudentDomainProfile,
)
from src.domain.value_objects.status import RiskStatus

logger = structlog.get_logger(__name__)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from src.core.identifiers import EntityID


@dataclass
class AdaptiveEngineConfig:
    """Configuration for the adaptive evaluation engine."""

    # Smoothing factor for EWMA Mean (0.3 = responsive)
    alpha: float = 0.3

    # Smoothing factor for Trends (0.2 = longer memory)
    gamma: float = 0.2

    # Variance regularization (shrinkage lambda)
    lambda_peer: float = 100.0

    # Stability regularization for personalized volatility
    # Equivalent to a 1.2 standard deviation floor in z-peer space
    lambda_stability: float = 1.5

    # Thresholds for volatility-aware drift (normalized_drift)
    drift_elevated_threshold: float = -2.5
    drift_critical_threshold: float = -4.5

    # Thresholds for multi-week trend signals
    # EWMA of drifts. A sustained negative drift of -0.3 is significant.
    trend_alert_threshold: float = -0.3

    # Thresholds for peer-relative classification (absolute safety net)
    peer_failure_threshold: float = -2.5
    peer_critical_threshold: float = -4.0

    # Confidence constant
    confidence_k: float = 0.5


class AdaptiveAnomalyEngine:
    """
    Adaptive Evaluation Engine (Tier 1 Evolution).

    Models student performance using:
    1. Regularized Peer-Normalization (z-peer)
    2. Adaptive Volatility-Aware Drift (p-signal)
    3. Multi-week Trend Persistence
    4. Systemic Breadth (Cross-domain decline)
    """

    def __init__(self, config: AdaptiveEngineConfig | None = None) -> None:
        """Initialize the engine with configuration."""
        self.config = config or AdaptiveEngineConfig()

    def run(
        self,
        student_data: Mapping[EntityID, Sequence[Mapping[str, Any]]],
        history_set: set[tuple[EntityID, int, int, int]],
    ) -> tuple[list[dict[str, Any]], dict[EntityID, RiskStatus]]:
        """
        Run the adaptive evaluation pipeline.

        Returns:
            A tuple of (new_history_records, latest_risk_statuses).
        """
        logger.info('AdaptiveEngine: Starting T1 evaluation...')

        new_history_records: list[dict[str, Any]] = []
        risk_statuses: dict[EntityID, RiskStatus] = {}

        for sid, raw_records in student_data.items():
            # 1. Feature Extraction
            measurements = self._parse_measurements(sid, raw_records)

            # 2. Sequential Evaluation (Online Learning)
            results = self._evaluate_student_timeline(sid, measurements, history_set)

            # 3. Persistence Mapping
            for res in results:
                if (sid, res.academic_year, res.semester, res.week) not in history_set:
                    new_history_records.append(self._map_to_persistence(res))

                risk_statuses[sid] = res.risk_status

        logger.info(
            'AdaptiveEngine: T1 Evaluation completed',
            new_records=len(new_history_records),
        )
        return new_history_records, risk_statuses

    def _parse_measurements(
        self,
        sid: EntityID,
        raw_records: Sequence[Mapping[str, Any]],
    ) -> list[ActivityMeasurement]:
        """Convert raw dictionary data into validated Measurement models."""
        measurements = []
        for r in raw_records:
            score = r.get('score') or r.get('avg_score') or 0.0
            course_avg = r.get('course_avg') or score
            course_std = r.get('course_std') or 0.0

            measurements.append(
                ActivityMeasurement(
                    sid=sid,
                    course_id=str(r.get('course_id', 'unknown')),
                    course_name=r.get('course_name'),
                    academic_year=int(r['academic_year']),
                    semester=int(r['semester']),
                    week=int(r['week']),
                    score=float(score),
                    course_avg=float(course_avg),
                    course_std=float(course_std),
                    domain=DomainMapper.map(r.get('course_name')),
                ),
            )
        return measurements

    def _evaluate_student_timeline(
        self,
        sid: EntityID,
        measurements: list[ActivityMeasurement],
        history_set: set[tuple[EntityID, int, int, int]],
    ) -> list[EvaluationResult]:
        """Evaluate a student's performance chronologically to update adaptive baselines."""
        weeks_map = defaultdict(list)
        for m in measurements:
            weeks_map[(m.academic_year, m.semester, m.week)].append(m)

        sorted_weeks = sorted(weeks_map.keys())

        # Adaptive State per Domain
        profiles: dict[str, StudentDomainProfile] = defaultdict(
            lambda: StudentDomainProfile(domain=DomainMapper.map(None)),
        )

        results = []
        for week_key in sorted_weeks:
            week_measurements = weeks_map[week_key]

            # Step A: Evaluate using PRIOR state
            res = self._evaluate_week(sid, week_measurements, profiles)
            results.append(res)

            # Step B: Update baselines with Weighted Anomaly Suppression
            self._update_baselines(week_measurements, profiles, res.risk_status)

        return results

    def _update_baselines(
        self,
        measurements: list[ActivityMeasurement],
        profiles: dict[str, StudentDomainProfile],
        status: RiskStatus,
    ) -> None:
        """Update adaptive baselines with learning rate suppression."""
        # 1. Determine Learning Rate suppression factor
        # Critical weeks: skip update (0.0)
        # Elevated weeks: slow update (0.2x)
        # Normal weeks: full update (1.0x)
        suppression = 1.0
        if status == RiskStatus.CRITICAL:
            suppression = 0.0
        elif status == RiskStatus.ELEVATED:
            suppression = 0.2

        if suppression == 0.0:
            return

        alpha = self.config.alpha * suppression

        for m in measurements:
            z_peer = self._calculate_z_peer(m)
            profiles[m.domain].update(z_peer, alpha=alpha, gamma=self.config.gamma)

    def _calculate_z_peer(self, m: ActivityMeasurement) -> float:
        """Calculate regularized peer-relative score."""
        regularized_std = math.sqrt((m.course_std**2) + self.config.lambda_peer)
        return (m.score - m.course_avg) / regularized_std

    def _evaluate_week(
        self,
        sid: EntityID,
        measurements: list[ActivityMeasurement],
        profiles: dict[str, StudentDomainProfile],
    ) -> EvaluationResult:
        """Score a single week and classify risk."""
        z_peers = []
        drifts = []
        normalized_drifts = []
        trends = []
        confidences = []

        total_score = 0.0

        for m in measurements:
            z_peer = self._calculate_z_peer(m)
            z_peers.append(z_peer)
            total_score += m.score

            profile = profiles[m.domain]

            # 1. Drift Calculation
            drift = 0.0
            normalized_drift = 0.0
            if profile.observation_count > 0:
                drift = z_peer - profile.ewma_z_peer
                # Volatility-Aware Normalization (Shrinkage on variance)
                volatility = math.sqrt(
                    profile.ewma_variance + self.config.lambda_stability
                )
                normalized_drift = drift / volatility

            drifts.append(drift)
            normalized_drifts.append(normalized_drift)
            trends.append(profile.ewma_drift)

            # 2. Confidence Score
            confidence = 1.0 - math.exp(
                -self.config.confidence_k * profile.observation_count
            )
            confidences.append(confidence)

        # 3. Systemic Breadth: Ratio of domains showing negative drift
        negative_drift_count = sum(1 for d in drifts if d < -0.5)
        breadth = negative_drift_count / len(measurements)

        # 4. Aggregation
        avg_score = total_score / len(measurements)
        avg_z_peer = sum(z_peers) / len(z_peers)
        avg_drift = sum(drifts) / len(drifts)
        avg_normalized_drift = sum(normalized_drifts) / len(normalized_drifts)
        avg_trend = sum(trends) / len(trends)
        avg_confidence = sum(confidences) / len(confidences)

        # Worst-case signals
        min_z_peer = min(z_peers)
        min_normalized_drift = min(normalized_drifts)

        # 5. Risk Classification
        risk_status = self._classify_risk(
            min_z_peer=min_z_peer,
            avg_normalized_drift=avg_normalized_drift,
            min_normalized_drift=min_normalized_drift,
            avg_trend=avg_trend,
            breadth=breadth,
            domain_count=len(measurements),
            confidence=avg_confidence,
        )

        return EvaluationResult(
            sid=sid,
            academic_year=measurements[0].academic_year,
            semester=measurements[0].semester,
            week=measurements[0].week,
            avg_score=avg_score,
            avg_z_peer=avg_z_peer,
            avg_drift=avg_drift,
            avg_normalized_drift=avg_normalized_drift,
            trend_score=avg_trend,
            confidence=avg_confidence,
            systemic_breadth=breadth,
            risk_status=risk_status,
            is_anomaly=(risk_status != RiskStatus.NORMAL),
            metadata={
                'min_z_peer': min_z_peer,
                'min_normalized_drift': min_normalized_drift,
            },
        )

    def _classify_risk(
        self,
        min_z_peer: float,
        avg_normalized_drift: float,
        min_normalized_drift: float,
        avg_trend: float,
        breadth: float,
        domain_count: int,
        confidence: float,
    ) -> RiskStatus:
        """Volatility-aware and persistence-aware classification policy."""

        # 0. Handle Cold Start
        # We need at least ~2 weeks of data (confidence > 0.4) to conclude a personal drop.
        if confidence < 0.4:
            # Fallback to absolute peer failure if it's extreme
            if min_z_peer < self.config.peer_critical_threshold:
                return RiskStatus.CRITICAL
            return RiskStatus.NORMAL

        # 1. Absolute Peer Failure (Critical safety net)
        if min_z_peer < self.config.peer_critical_threshold:
            return RiskStatus.CRITICAL

        # 2. Severe Personalized Collapse (Volatility-aware)
        # Needs high confidence
        if confidence > 0.6:
            # Single domain collapse
            if min_normalized_drift < self.config.drift_critical_threshold:
                return RiskStatus.CRITICAL

            # Systemic decline (multiple domains dropping moderately)
            # Only apply if measuring > 1 domain
            if (
                domain_count > 1
                and avg_normalized_drift < self.config.drift_elevated_threshold
                and breadth > 0.5
            ):
                return RiskStatus.CRITICAL

            # 3. Trend Persistence (Sustained decline)
            # If the multi-week trend is consistently negative
            if avg_trend < self.config.trend_alert_threshold:
                return RiskStatus.ELEVATED

            # 4. Moderate Personalized Drift
            if min_normalized_drift < self.config.drift_elevated_threshold:
                return RiskStatus.ELEVATED

        # 5. Moderate Peer Failure (Absolute fallback)
        if min_z_peer < self.config.peer_failure_threshold:
            return RiskStatus.ELEVATED

        return RiskStatus.NORMAL

    def _map_to_persistence(self, res: EvaluationResult) -> dict[str, Any]:
        """Map EvaluationResult back to legacy database schema with enhanced signals."""
        return {
            'history_id': generate_uuid(),
            'sid': res.sid,
            'academic_year': res.academic_year,
            'semester': res.semester,
            'week': res.week,
            'baseline_avg': res.avg_z_peer - res.avg_drift,
            'baseline_std': res.confidence,
            'current_score_avg': res.avg_score,
            'z_score': res.avg_normalized_drift,
            'avg_normalized_drift': res.avg_normalized_drift,
            'trend_score': res.trend_score,
            'confidence': res.confidence,
            'systemic_breadth': res.systemic_breadth,
            'anomaly_flag': res.risk_status.value,
        }


# Alias for backward compatibility
ZScore = AdaptiveAnomalyEngine
