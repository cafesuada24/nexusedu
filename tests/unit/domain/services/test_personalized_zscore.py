"""Tests for the Adaptive Evaluation Engine (Personalized Logic)."""

import uuid
from typing import Any

import pytest

from src.domain.services.anomaly_engine.zscore import ZScore
from src.domain.value_objects.status import RiskStatus


@pytest.fixture
def zscore():
    return ZScore()


def test_zscore_personalized_pattern_stem_vs_humanities(zscore):
    """
    Verify that a student's personal bias is accounted for.
    """
    sid = uuid.uuid4()
    
    history = []
    # Provide 10 weeks of consistent history
    for week in range(1, 11):
        # STEM Subject: Student gets 95, Course Avg 75, Std 10
        # regularized_std = sqrt(10^2 + 25) = sqrt(125) = 11.18
        # z-peer = (95-75)/11.18 = +1.79
        history.append({
            'sid': sid, 'course_id': 'CS101', 'course_name': 'Programming',
            'score': 95.0, 'course_avg': 75.0, 'course_std': 10.0,
            'academic_year': 1, 'semester': 1, 'week': week
        })
        # Humanities Subject: Student gets 45, Course Avg 50, Std 10
        # z-peer = (45-50)/11.18 = -0.45
        history.append({
            'sid': sid, 'course_id': 'PH101', 'course_name': 'Philosophy',
            'score': 45.0, 'course_avg': 50.0, 'course_std': 10.0,
            'academic_year': 1, 'semester': 1, 'week': week
        })

    # Week 11:
    # 1. Philosophy score remains 45 (z-peer -0.45). This matches their profile.
    # 2. Programming score crashes to 60 (z-peer = (60-75)/11.18 = -1.34).
    #    Drift = -1.34 - 1.79 = -3.13. This is a huge negative drift.
    week11 = [
        {
            'sid': sid, 'course_id': 'CS101', 'course_name': 'Programming',
            'score': 60.0, 'course_avg': 75.0, 'course_std': 10.0,
            'academic_year': 1, 'semester': 1, 'week': 11
        },
        {
            'sid': sid, 'course_id': 'PH101', 'course_name': 'Philosophy',
            'score': 45.0, 'course_avg': 50.0, 'course_std': 10.0,
            'academic_year': 1, 'semester': 1, 'week': 11
        }
    ]
    
    student_data = {sid: history + week11}
    new_records, risk_statuses = zscore.run(student_data, set())

    # Should be CRITICAL because drift is -3.13 (< -2.5 threshold)
    assert risk_statuses[sid] == RiskStatus.CRITICAL


def test_zscore_confidence_aware_warmup(zscore):
    """
    Verify that anomalies are NOT triggered without enough history (confidence).
    """
    sid = uuid.uuid4()
    
    # Only 1 week of history
    history = [
        {
            'sid': sid, 'course_id': 'CS101', 'course_name': 'Programming',
            'score': 95.0, 'course_avg': 75.0, 'course_std': 10.0,
            'academic_year': 1, 'semester': 1, 'week': 1
        }
    ]
    
    # Week 2: Huge drop
    week2 = [
        {
            'sid': sid, 'course_id': 'CS101', 'course_name': 'Programming',
            'score': 60.0, 'course_avg': 75.0, 'course_std': 10.0,
            'academic_year': 1, 'semester': 1, 'week': 2
        }
    ]
    
    student_data = {sid: history + week2}
    new_records, risk_statuses = zscore.run(student_data, set())

    # Confidence for N=1 is low. Drift is -3.13 but confidence check 
    # `if confidence > 0.6` (needs ~2 observations) prevents personalized alert.
    # Peer failure check `min_z_peer < -2.5` also doesn't trigger as z-peer is -1.34.
    assert risk_statuses[sid] == RiskStatus.NORMAL


def test_zscore_absolute_peer_safety_net(zscore):
    """
    Verify that even with low history, an absolute catastrophe is caught.
    """
    sid = uuid.uuid4()
    
    # Week 1: Total disaster (raw 20 vs avg 80)
    # z-peer = (20-80)/sqrt(125) = -60/11.18 = -5.36
    week1 = [
        {
            'sid': sid, 'course_id': 'CS101', 'course_name': 'Programming',
            'score': 20.0, 'course_avg': 80.0, 'course_std': 10.0,
            'academic_year': 1, 'semester': 1, 'week': 1
        }
    ]
    
    student_data = {sid: week1}
    new_records, risk_statuses = zscore.run(student_data, set())

    # caught by `peer_critical_threshold` (-3.5)
    assert risk_statuses[sid] == RiskStatus.CRITICAL
