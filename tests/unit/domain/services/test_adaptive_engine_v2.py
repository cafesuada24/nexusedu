"""Production-grade statistical and behavioral test suite for AdaptiveAnomalyEngine.

Focus:
- Statistical invariants
- Numerical robustness
- Temporal consistency
- False positive suppression
- Adaptive baseline behavior
- Confidence evolution
- Drift stability
- Adversarial scenarios
"""

from __future__ import annotations

import math
import random
import uuid
from typing import TYPE_CHECKING

import pytest

from src.domain.services.anomaly_engine.zscore import (
    AdaptiveAnomalyEngine,
    AdaptiveEngineConfig,
)
from src.domain.value_objects.status import RiskStatus

if TYPE_CHECKING:
    from collections.abc import Callable

# =========================================================
# Fixtures / Helpers
# =========================================================


@pytest.fixture
def engine() -> AdaptiveAnomalyEngine:
    return AdaptiveAnomalyEngine(
        AdaptiveEngineConfig(
            alpha=0.3,
            confidence_k=0.5,
        ),
    )


def make_record(
    *,
    sid: uuid.UUID,
    week: int,
    score: float,
    course_avg: float = 80.0,
    course_std: float = 10.0,
    course_name: str = "STEM",
    semester: int = 1,
    year: int = 1,
) -> dict:
    return {
        "sid": sid,
        "course_id": course_name,
        "course_name": course_name,
        "score": score,
        "course_avg": course_avg,
        "course_std": course_std,
        "academic_year": year,
        "semester": semester,
        "week": week,
    }


def build_history(
    *,
    sid: uuid.UUID,
    weeks: int,
    score_fn: Callable[[int], float],
    course_avg: float = 80.0,
    course_std: float = 10.0,
    course_name: str = "STEM",
) -> list[dict]:
    return [
        make_record(
            sid=sid,
            week=w,
            score=score_fn(w),
            course_avg=course_avg,
            course_std=course_std,
            course_name=course_name,
        )
        for w in range(1, weeks + 1)
    ]


# =========================================================
# Statistical Invariants
# =========================================================


def test_confidence_monotonicity(engine):
    """
    Confidence should never decrease as observations increase.
    """
    sid = uuid.uuid4()

    data = build_history(
        sid=sid,
        weeks=20,
        score_fn=lambda _: 90.0,
    )

    results, _ = engine.run({sid: data}, set())

    confidences = [r["baseline_std"] for r in results]

    assert all(
        c2 >= c1
        for c1, c2 in zip(confidences, confidences[1:], strict=False)
    )


def test_ewma_converges_under_constant_signal(engine):
    """
    Drift should converge toward zero for stable repeated behavior.
    """
    sid = uuid.uuid4()

    data = build_history(
        sid=sid,
        weeks=30,
        score_fn=lambda _: 90.0,
    )

    results, _ = engine.run({sid: data}, set())

    final_drift = results[-1]["z_score"]

    assert abs(final_drift) < 0.1


def test_identical_input_produces_stable_classification(engine):
    """
    Stable students should remain NORMAL indefinitely.
    """
    sid = uuid.uuid4()

    data = build_history(
        sid=sid,
        weeks=50,
        score_fn=lambda _: 88.0,
    )

    _, statuses = engine.run({sid: data}, set())

    assert statuses[sid] == RiskStatus.NORMAL


# =========================================================
# False Positive Suppression
# =========================================================


def test_random_noise_does_not_trigger_excessive_alerts(engine):
    """
    Stable gaussian noise should rarely trigger alerts.
    """
    sid = uuid.uuid4()
    rng = random.Random(42)

    data = build_history(
        sid=sid,
        weeks=100,
        score_fn=lambda _: 90.0 + rng.gauss(0, 2),
    )

    results, _ = engine.run({sid: data}, set())

    alerts = [
        r for r in results
        if r["anomaly_flag"] != RiskStatus.NORMAL.value
    ]

    alert_rate = len(alerts) / len(results)

    assert alert_rate < 0.05


def test_single_bad_week_does_not_create_long_term_alert(engine):
    """
    One anomalous week should not poison future classifications.
    """
    sid = uuid.uuid4()

    data = []

    for week in range(1, 31):
        score = 90.0

        if week == 15:
            score = 50.0

        data.append(make_record(
            sid=sid,
            week=week,
            score=score,
        ))

    results, statuses = engine.run({sid: data}, set())

    assert statuses[sid] == RiskStatus.NORMAL

    late_weeks = [r for r in results if r["week"] >= 20]

    assert all(
        r["anomaly_flag"] == RiskStatus.NORMAL.value
        for r in late_weeks
    )


# =========================================================
# Sparse History / Confidence Tests
# =========================================================


def test_new_student_does_not_trigger_alert(engine):
    """
    New students should not be aggressively classified.
    """
    sid = uuid.uuid4()

    data = [
        make_record(
            sid=sid,
            week=1,
            score=60.0,
        ),
    ]

    _, statuses = engine.run({sid: data}, set())

    assert statuses[sid] in {
        RiskStatus.NORMAL,
    }


def test_low_history_has_low_confidence(engine):
    """
    Confidence should remain low with few observations.
    """
    sid = uuid.uuid4()

    data = build_history(
        sid=sid,
        weeks=2,
        score_fn=lambda _: 90.0,
    )

    results, _ = engine.run({sid: data}, set())

    assert results[-1]["baseline_std"] < 0.7


# =========================================================
# Volatility Awareness
# =========================================================


def test_high_volatility_student_is_more_tolerant(engine):
    """
    Same drift should be less severe for volatile students.
    """
    sid_stable = uuid.uuid4()
    sid_volatile = uuid.uuid4()

    stable = build_history(
        sid=sid_stable,
        weeks=20,
        score_fn=lambda _: 90.0,
    )

    volatile = build_history(
        sid=sid_volatile,
        weeks=20,
        score_fn=lambda w: 90.0 + (10 if w % 2 == 0 else -10),
    )

    stable.append(make_record(
        sid=sid_stable,
        week=21,
        score=60.0,
    ))

    volatile.append(make_record(
        sid=sid_volatile,
        week=21,
        score=60.0,
    ))

    _, statuses = engine.run({
        sid_stable: stable,
        sid_volatile: volatile,
    }, set())

    assert statuses[sid_stable] != statuses[sid_volatile]


# =========================================================
# Trend Persistence
# =========================================================


def test_sustained_decline_triggers_alert(engine):
    """
    Persistent moderate deterioration should escalate.
    """
    sid = uuid.uuid4()

    data = []

    for week in range(1, 11):
        data.append(make_record(
            sid=sid,
            week=week,
            score=95.0,
        ))

    for week in range(11, 21):
        score = 95.0 - (week - 10) * 2
        data.append(make_record(
            sid=sid,
            week=week,
            score=score,
        ))

    _, statuses = engine.run({sid: data}, set())

    assert statuses[sid] in {
        RiskStatus.ELEVATED,
        RiskStatus.CRITICAL,
    }


# =========================================================
# Breadth / Systemic Collapse
# =========================================================


def test_systemic_decline_is_worse_than_isolated(engine):
    """
    Multiple-domain deterioration should escalate strongly.
    """
    sid = uuid.uuid4()

    data = []

    domains = ["STEM", "Arts", "Humanities"]

    for week in range(1, 11):
        for domain in domains:
            data.append(make_record(
                sid=sid,
                week=week,
                score=90.0,
                course_name=domain,
            ))

    for domain in domains:
        data.append(make_record(
            sid=sid,
            week=11,
            score=70.0,
            course_name=domain,
        ))

    _, statuses = engine.run({sid: data}, set())

    assert statuses[sid] == RiskStatus.CRITICAL


# =========================================================
# Temporal Robustness
# =========================================================


def test_missing_weeks_do_not_break_engine(engine):
    """
    Sparse timelines should remain numerically stable.
    """
    sid = uuid.uuid4()

    data = [
        make_record(sid=sid, week=1, score=90),
        make_record(sid=sid, week=2, score=90),
        make_record(sid=sid, week=8, score=88),
        make_record(sid=sid, week=15, score=87),
    ]

    results, statuses = engine.run({sid: data}, set())

    assert len(results) > 0
    assert sid in statuses


def test_semester_transition_does_not_explode(engine):
    """
    Semester boundaries should not create numerical instability.
    """
    sid = uuid.uuid4()

    data = []

    for week in range(1, 16):
        data.append(make_record(
            sid=sid,
            week=week,
            score=90,
            semester=1,
        ))

    for week in range(1, 16):
        data.append(make_record(
            sid=sid,
            week=week,
            score=88,
            semester=2,
        ))

    results, _ = engine.run({sid: data}, set())

    assert all(
        math.isfinite(r["z_score"])
        for r in results
    )


# =========================================================
# Numerical Robustness
# =========================================================


def test_near_zero_variance_is_stable(engine):
    """
    Tiny course variance should not explode z-values.
    """
    sid = uuid.uuid4()

    data = build_history(
        sid=sid,
        weeks=10,
        score_fn=lambda _: 90,
        course_std=0.00001,
    )

    results, _ = engine.run({sid: data}, set())

    assert all(
        math.isfinite(r["z_score"])
        for r in results
    )


def test_huge_variance_is_stable(engine):
    """
    Extremely noisy courses should remain numerically safe.
    """
    sid = uuid.uuid4()

    data = build_history(
        sid=sid,
        weeks=10,
        score_fn=lambda _: 90,
        course_std=1_000_000,
    )

    results, _ = engine.run({sid: data}, set())

    assert all(
        math.isfinite(r["z_score"])
        for r in results
    )


def test_nan_input_is_handled_gracefully(engine):
    """
    NaN input should not silently propagate.
    """
    sid = uuid.uuid4()

    data = [
        make_record(
            sid=sid,
            week=1,
            score=float("nan"),
        ),
    ]

    with pytest.raises((ValueError, TypeError)):
        engine.run({sid: data}, set())


def test_inf_input_is_handled_gracefully(engine):
    """
    Infinite values should fail safely.
    """
    sid = uuid.uuid4()

    data = [
        make_record(
            sid=sid,
            week=1,
            score=float("inf"),
        ),
    ]

    with pytest.raises((ValueError, OverflowError)):
        engine.run({sid: data}, set())


# =========================================================
# Threshold Boundary Tests
# =========================================================


@pytest.mark.parametrize(
    ("drift", "expected"),
    [
        (-1.49, RiskStatus.NORMAL),
        (-1.51, RiskStatus.ELEVATED),
        (-2.99, RiskStatus.ELEVATED),
        (-3.01, RiskStatus.CRITICAL),
    ],
)
def test_threshold_boundaries(
    engine,
    drift,
    expected,
):
    """
    Threshold comparisons should behave deterministically.
    """

    status = engine._classify_risk(
        min_z_peer=-1.0,
        avg_normalized_drift=drift,
        min_normalized_drift=drift,
        avg_trend=0.0,
        breadth=0.0,
        domain_count=1,
        confidence=1.0,
    )

    assert status == expected


# =========================================================
# Adversarial Oscillation Tests
# =========================================================


def test_oscillating_student_does_not_break_adaptation(engine):
    """
    Rapid oscillation should not destabilize the engine.
    """
    sid = uuid.uuid4()

    data = build_history(
        sid=sid,
        weeks=40,
        score_fn=lambda w: 100 if w % 2 == 0 else 60,
    )

    results, statuses = engine.run({sid: data}, set())

    assert all(
        math.isfinite(r["z_score"])
        for r in results
    )

    assert sid in statuses


# =========================================================
# Persistence Mapping Integrity
# =========================================================


def test_persistence_mapping_contains_required_fields(engine):
    """
    Persistence records must remain schema compatible.
    """
    sid = uuid.uuid4()

    data = build_history(
        sid=sid,
        weeks=5,
        score_fn=lambda _: 90,
    )

    results, _ = engine.run({sid: data}, set())

    required = {
        "history_id",
        "sid",
        "academic_year",
        "semester",
        "week",
        "baseline_avg",
        "baseline_std",
        "current_score_avg",
        "z_score",
        "anomaly_flag",
    }

    assert required.issubset(results[-1].keys())
