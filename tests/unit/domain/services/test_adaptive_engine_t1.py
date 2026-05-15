"""Tests for the Adaptive Evaluation Engine Tier 1 Evolution."""

import uuid
from typing import Any

import pytest

from src.domain.services.anomaly_engine.zscore import (
    AdaptiveAnomalyEngine,
    AdaptiveEngineConfig,
)
from src.domain.value_objects.status import RiskStatus


@pytest.fixture
def engine():
    return AdaptiveAnomalyEngine()


def test_volatility_awareness(engine):
    """
    Verify that a high-volatility student is more resistant to alerts
    than a low-volatility student for the same drift.
    """
    sid_stable = uuid.uuid4()
    sid_volatile = uuid.uuid4()

    # Stable Student History: Always gets 90 (z-peer ~1.0)
    history_stable = []
    # Volatile Student History: Swings between 70 and 100 (z-peer ~0.5 to 2.0)
    history_volatile = []

    for week in range(1, 11):
        # Stable
        history_stable.append(
            {
                'sid': sid_stable,
                'course_id': 'C1',
                'course_name': 'STEM',
                'score': 90.0,
                'course_avg': 80.0,
                'course_std': 10.0,
                'academic_year': 1,
                'semester': 1,
                'week': week,
            }
        )
        # Volatile
        score = 85.0 + (15.0 if week % 2 == 0 else -15.0)
        history_volatile.append(
            {
                'sid': sid_volatile,
                'course_id': 'C1',
                'course_name': 'STEM',
                'score': score,
                'course_avg': 80.0,
                'course_std': 10.0,
                'academic_year': 1,
                'semester': 1,
                'week': week,
            }
        )

    # Week 11: Both drop to 70 (z-peer = (70-80)/sqrt(125) = -0.89)
    # Drift for stable: -0.89 - 0.89 = -1.78
    # Drift for volatile: -0.89 - 0.89 = -1.78
    # BUT volatile student has high ewma_variance, so normalized_drift is small.
    week11_data = [
        {
            'sid': sid_stable,
            'course_id': 'C1',
            'course_name': 'STEM',
            'score': 70.0,
            'course_avg': 80.0,
            'course_std': 10.0,
            'academic_year': 1,
            'semester': 1,
            'week': 11,
        },
        {
            'sid': sid_volatile,
            'course_id': 'C1',
            'course_name': 'STEM',
            'score': 70.0,
            'course_avg': 80.0,
            'course_std': 10.0,
            'academic_year': 1,
            'semester': 1,
            'week': 11,
        },
    ]

    student_data = {
        sid_stable: history_stable + [week11_data[0]],
        sid_volatile: history_volatile + [week11_data[1]],
    }

    _, risk_statuses = engine.run(student_data, set())

    # Stable student should be ELEVATED (due to low volatility, small drop is significant)
    # Volatile student should be NORMAL (due to high volatility)
    assert risk_statuses[sid_stable] == RiskStatus.ELEVATED
    assert risk_statuses[sid_volatile] == RiskStatus.NORMAL


def test_trend_persistence(engine):
    """
    Verify that sustained moderate decline triggers an alert via Trend Score.
    """
    sid = uuid.uuid4()

    # 10 weeks of high performance
    history = []
    for week in range(1, 11):
        history.append(
            {
                'sid': sid,
                'course_id': 'C1',
                'course_name': 'STEM',
                'score': 95.0,
                'course_avg': 80.0,
                'course_std': 10.0,
                'academic_year': 1,
                'semester': 1,
                'week': week,
            }
        )

    # Weeks 11-14: Slow, steady decline (each week -0.5 z-peer drift)
    # Individually, -0.5 drift is NORMAL.
    # But the EWMA Trend Score will accumulate this.
    decline = []
    for week in range(11, 15):
        score = 95.0 - (5.0 * (week - 10))
        decline.append(
            {
                'sid': sid,
                'course_id': 'C1',
                'course_name': 'STEM',
                'score': score,
                'course_avg': 80.0,
                'course_std': 10.0,
                'academic_year': 1,
                'semester': 1,
                'week': week,
            }
        )

    student_data = {sid: history + decline}
    _, risk_statuses = engine.run(student_data, set())

    # By Week 14, the trend should be negative enough to trigger ELEVATED
    assert risk_statuses[sid] == RiskStatus.ELEVATED


def test_systemic_breadth(engine):
    """
    Verify that dropping moderately across MANY domains is CRITICAL (Systemic),
    while dropping severely in only ONE is also CRITICAL (Isolated).
    """
    sid_systemic = uuid.uuid4()
    sid_isolated = uuid.uuid4()

    # 10 weeks history for both
    history_sys = []
    history_iso = []
    for week in range(1, 11):
        for domain in ['STEM', 'Humanities', 'Arts']:
            history_sys.append(
                {
                    'sid': sid_systemic,
                    'course_id': domain,
                    'course_name': domain,
                    'score': 90.0,
                    'course_avg': 80.0,
                    'course_std': 10.0,
                    'academic_year': 1,
                    'semester': 1,
                    'week': week,
                }
            )
            history_iso.append(
                {
                    'sid': sid_isolated,
                    'course_id': domain,
                    'course_name': domain,
                    'score': 90.0,
                    'course_avg': 80.0,
                    'course_std': 10.0,
                    'academic_year': 1,
                    'semester': 1,
                    'week': week,
                }
            )

    # Week 11 Systemic: All 3 domains drop to 70 (Moderate drift each)
    week11_sys = [
        {
            'sid': sid_systemic,
            'course_id': d,
            'course_name': d,
            'score': 70.0,
            'course_avg': 80.0,
            'course_std': 10.0,
            'academic_year': 1,
            'semester': 1,
            'week': 11,
        }
        for d in ['STEM', 'Humanities', 'Arts']
    ]

    # Week 11 Isolated: Only STEM drops to 40 (Severe drift), others stay 90
    week11_iso = [
        {
            'sid': sid_isolated,
            'course_id': 'STEM',
            'course_name': 'STEM',
            'score': 40.0,
            'course_avg': 80.0,
            'course_std': 10.0,
            'academic_year': 1,
            'semester': 1,
            'week': 11,
        },
        {
            'sid': sid_isolated,
            'course_id': 'Humanities',
            'course_name': 'Humanities',
            'score': 90.0,
            'course_avg': 80.0,
            'course_std': 10.0,
            'academic_year': 1,
            'semester': 1,
            'week': 11,
        },
        {
            'sid': sid_isolated,
            'course_id': 'Arts',
            'course_name': 'Arts',
            'score': 90.0,
            'course_avg': 80.0,
            'course_std': 10.0,
            'academic_year': 1,
            'semester': 1,
            'week': 11,
        },
    ]

    student_data = {
        sid_systemic: history_sys + week11_sys,
        sid_isolated: history_iso + week11_iso,
    }

    _, risk_statuses = engine.run(student_data, set())

    # Both should be CRITICAL but for different reasons
    assert risk_statuses[sid_systemic] == RiskStatus.CRITICAL
    assert risk_statuses[sid_isolated] == RiskStatus.CRITICAL


def test_alpha_suppression_prevents_contamination(engine):
    """
    Verify that the baseline mean doesn't "follow" the student down during elevated weeks.
    """
    sid = uuid.uuid4()

    # 10 weeks of 90s
    history = []
    for week in range(1, 11):
        history.append(
            {
                'sid': sid,
                'course_id': 'C1',
                'course_name': 'STEM',
                'score': 90.0,
                'course_avg': 80.0,
                'course_std': 10.0,
                'academic_year': 1,
                'semester': 1,
                'week': week,
            }
        )

    # Week 11: Drops to 75 (ELEVATED)
    week11 = [
        {
            'sid': sid,
            'course_id': 'C1',
            'course_name': 'STEM',
            'score': 75.0,
            'course_avg': 80.0,
            'course_std': 10.0,
            'academic_year': 1,
            'semester': 1,
            'week': 11,
        }
    ]

    # Week 12: Stays 75 (Should STILL be ELEVATED because baseline didn't update fully)
    week12 = [
        {
            'sid': sid,
            'course_id': 'C1',
            'course_name': 'STEM',
            'score': 75.0,
            'course_avg': 80.0,
            'course_std': 10.0,
            'academic_year': 1,
            'semester': 1,
            'week': 12,
        }
    ]

    student_data = {sid: history + week11 + week12}
    new_records, risk_statuses = engine.run(student_data, set())

    # If alpha suppression works, Week 12 is still ELEVATED.
    # If not, the baseline would have dropped and Week 12 might look NORMAL.
    assert risk_statuses[sid] == RiskStatus.ELEVATED

    # Check that Week 12 record exists and is ELEVATED
    w12_rec = next(r for r in new_records if r['week'] == 12)
    assert w12_rec['anomaly_flag'] == RiskStatus.ELEVATED.value
