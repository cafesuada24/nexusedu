"""Tests for the Adaptive Evaluation Engine (Legacy Compatibility)."""

import uuid
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
    """Verify that a sharp drop in scores triggers an anomaly."""
    sid = uuid.uuid4()
    # Provide longer history for adaptive engine
    weekly_avgs = []
    for w in range(1, 11):
        # Good performance relative to peers
        weekly_avgs.append({
            'sid': sid, 'score': 90.0, 'course_avg': 70.0, 'course_std': 10.0,
            'academic_year': 2024, 'semester': 1, 'week': w
        })
    
    # Significant drop in Week 11
    weekly_avgs.append({
        'sid': sid, 'score': 30.0, 'course_avg': 70.0, 'course_std': 10.0,
        'academic_year': 2024, 'semester': 1, 'week': 11
    })
    
    student_data = {sid: weekly_avgs}
    new_records, risk_statuses = zscore.run(student_data, set())

    assert risk_statuses[sid] == RiskStatus.CRITICAL


def test_zscore_avoid_duplicate_history(zscore):
    """Verify that existing history records are not recreated."""
    sid = uuid.uuid4()
    weekly_avgs = [
        {'sid': sid, 'score': 100.0, 'course_avg': 80.0, 'academic_year': 1, 'semester': 1, 'week': 1},
        {'sid': sid, 'score': 100.0, 'course_avg': 80.0, 'academic_year': 1, 'semester': 1, 'week': 2},
    ]
    student_data = {sid: weekly_avgs}
    # If BOTH weeks are in history_set, no new records should be emitted
    existing_history = {
        (sid, 1, 1, 1),
        (sid, 1, 1, 2),
    }

    new_records, risk_statuses = zscore.run(student_data, existing_history)

    assert len(new_records) == 0
    assert risk_statuses[sid] == RiskStatus.NORMAL


def test_zscore_exact_boundary_deviation(zscore):
    """Verify risk thresholds."""
    sid = uuid.uuid4()

    # Provide stable baseline
    weekly_avgs = []
    for w in range(1, 11):
        weekly_avgs.append({
            'sid': sid, 'score': 100.0, 'course_avg': 80.0, 'course_std': 10.0,
            'academic_year': 1, 'semester': 1, 'week': w
        })
        
    # Week 11: absolute drop
    weekly_avgs.append({
        'sid': sid, 'score': 40.0, 'course_avg': 80.0, 'course_std': 10.0,
        'academic_year': 1, 'semester': 1, 'week': 11
    })
    
    student_data = {sid: weekly_avgs}
    new_records, risk_statuses = zscore.run(student_data, set())

    assert risk_statuses[sid] == RiskStatus.CRITICAL
