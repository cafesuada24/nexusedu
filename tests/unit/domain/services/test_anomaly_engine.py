"""Tests for the ZScore pure domain service."""

import uuid
from collections import defaultdict
from typing import Any

import pytest

from src.domain.services.anomaly_engine.zscore import ZScore
from src.domain.value_objects.status import RiskStatus


@pytest.fixture
def zscore():
    return ZScore()


def test_zscore_empty_data(zscore):
    """Verify zscore handles no data gracefully."""
    new_records, risk_statuses = zscore.run({}, set())
    assert new_records == []
    assert risk_statuses == {}


def test_zscore_significant_drop_detection(zscore):
    """Verify that a sharp drop in scores triggers an anomaly (Elevated)."""
    sid = uuid.uuid4()
    # Data: 3 weeks of high scores, then 1 week of low score
    weekly_avgs = [
        {'sid': sid, 'avg_score': 90.0, 'academic_year': 2024, 'semester': 1, 'week': 1},
        {'sid': sid, 'avg_score': 92.0, 'academic_year': 2024, 'semester': 1, 'week': 2},
        {'sid': sid, 'avg_score': 88.0, 'academic_year': 2024, 'semester': 1, 'week': 3},
        {'sid': sid, 'avg_score': 70.0, 'academic_year': 2024, 'semester': 1, 'week': 4},
    ]
    student_data = {sid: weekly_avgs}

    new_records, risk_statuses = zscore.run(student_data, set())

    # Verify risk status
    assert risk_statuses[sid] == RiskStatus.ELEVATED

    # Should have 3 records (Week 2, 3, 4) since Week 1 has no previous history for baseline
    assert len(new_records) == 3

    # Week 4 should be ELEVATED
    week4_record = next(r for r in new_records if r['week'] == 4)
    assert week4_record['anomaly_flag'] == RiskStatus.ELEVATED.value
    assert week4_record['z_score'] < -1.5


def test_zscore_critical_drop_ratio(zscore):
    """Verify that a drop below the critical ratio triggers an anomaly (Critical)."""
    sid = uuid.uuid4()
    # Constant high scores, then sudden drop
    weekly_avgs = [
        {'sid': sid, 'avg_score': 100.0, 'academic_year': 1, 'semester': 1, 'week': 1},
        {'sid': sid, 'avg_score': 100.0, 'academic_year': 1, 'semester': 1, 'week': 2},
        {'sid': sid, 'avg_score': 60.0, 'academic_year': 1, 'semester': 1, 'week': 3}, # 0.6 < 0.7 ratio
    ]
    student_data = {sid: weekly_avgs}

    new_records, risk_statuses = zscore.run(student_data, set())

    assert risk_statuses[sid] == RiskStatus.CRITICAL
    week3_record = next(r for r in new_records if r['week'] == 3)
    assert week3_record['anomaly_flag'] == RiskStatus.CRITICAL.value


def test_zscore_avoid_duplicate_history(zscore):
    """Verify that existing history records are not recreated."""
    sid = uuid.uuid4()
    weekly_avgs = [
        {'sid': sid, 'avg_score': 100.0, 'academic_year': 1, 'semester': 1, 'week': 1},
        {'sid': sid, 'avg_score': 100.0, 'academic_year': 1, 'semester': 1, 'week': 2},
    ]
    student_data = {sid: weekly_avgs}
    existing_history = {
        (sid, 1, 1, 2),
    }

    new_records, risk_statuses = zscore.run(student_data, existing_history)

    # Should be empty since W2 exists and W1 is baseline
    assert len(new_records) == 0
    assert risk_statuses[sid] == RiskStatus.NORMAL


def test_zscore_exact_boundary_deviation(zscore):
    """Verify that exactly a 20% deviation triggers the correct risk threshold."""
    sid = uuid.uuid4()

    # Baseline average is 100.
    # Exactly 80 is a 20% drop.
    # Current implementation:
    # 1. Calculate Z-score
    # 2. If current_avg < baseline_avg * 0.7 -> CRITICAL
    # 3. Else if z_score < threshold (-1.5) -> ELEVATED

    # We need a stable baseline with some variance to get a meaningful Z-score
    weekly_avgs = [
        {'sid': sid, 'avg_score': 100.0, 'academic_year': 1, 'semester': 1, 'week': 1},
        {'sid': sid, 'avg_score': 105.0, 'academic_year': 1, 'semester': 1, 'week': 2},
        {'sid': sid, 'avg_score': 95.0, 'academic_year': 1, 'semester': 1, 'week': 3},
        # Baseline mean: 100, Std: sqrt(((0)^2 + (5)^2 + (-5)^2)/3) = sqrt(50/3) = 4.08
        # A drop to 93.8 (Z = (93.8-100)/4.08 = -1.51) should trigger ELEVATED
        {'sid': sid, 'avg_score': 93.8, 'academic_year': 1, 'semester': 1, 'week': 4},
        # A drop to 60 (< 100 * 0.7) should trigger CRITICAL
        {'sid': sid, 'avg_score': 60.0, 'academic_year': 1, 'semester': 1, 'week': 5},
    ]
    student_data = {sid: weekly_avgs}

    new_records, risk_statuses = zscore.run(student_data, set())

    week4_record = next(r for r in new_records if r['week'] == 4)
    week5_record = next(r for r in new_records if r['week'] == 5)

    assert week4_record['anomaly_flag'] == RiskStatus.ELEVATED.value
    assert week5_record['anomaly_flag'] == RiskStatus.CRITICAL.value
