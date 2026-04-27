"""Tests for the Z-Score anomaly detection algorithm."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.database.manager import DatabaseManager

def test_zscore_calculation_flow(test_db_manager: DatabaseManager) -> None:
    """Verify the math and flow of the Z-score algorithm."""
    # 1. Setup Student in SIS
    test_db_manager.ingest_records('sis_db', 'students', [
        {'sid': 'S_ANOMALY', 'student_name': 'Bob', 'email': 'bob@example.com'},
    ])

    # 2. Setup Activities in LMS
    # Need historical data to establish baseline
    activities = [
        # Semester 1 (High)
        {'sid': 'S_ANOMALY', 'academic_year': 2023, 'semester': 1, 'score': 90},
        {'sid': 'S_ANOMALY', 'academic_year': 2023, 'semester': 1, 'score': 95},
        # Semester 2 (High)
        {'sid': 'S_ANOMALY', 'academic_year': 2023, 'semester': 2, 'score': 92},
        # Current Semester (Significant Drop)
        {'sid': 'S_ANOMALY', 'academic_year': 2024, 'semester': 1, 'score': 40},
    ]
    test_db_manager.ingest_records('lms_db', 'activities', activities)

    # 3. Run Anomaly Engine
    test_db_manager.run_anomaly_engine()

    # 4. Verify History
    history = test_db_manager.execute(
        'sis_db', "SELECT * FROM student_status_history WHERE sid = 'S_ANOMALY'",
    )
    # We expect 2 entries in history (Semester 2 has baseline from S1, Semester 3 has baseline from S1+S2)
    # The current one (2024, 1) should show a Significant or Critical Drop
    assert len(history) >= 1

    latest = sorted(history, key=lambda x: (x['academic_year'], x['semester']))[-1]
    assert latest['academic_year'] == 2024
    assert latest['anomaly_flag'] != 'Normal'

    # 5. Verify Student Risk Status updated
    student = test_db_manager.execute(
        'sis_db',
        "SELECT current_risk_status, intervention_status FROM students WHERE sid = 'S_ANOMALY'",
    )
    assert student[0]['current_risk_status'] == latest['anomaly_flag']
    assert student[0]['intervention_status'] == 'new'

def test_normal_student_flow(test_db_manager: DatabaseManager) -> None:
    """Verify that consistent performance stays 'Normal'."""
    test_db_manager.ingest_records('sis_db', 'students', [
        {'sid': 'S_NORMAL', 'student_name': 'Charlie', 'email': 'charlie@example.com'},
    ])

    activities = [
        {'sid': 'S_NORMAL', 'academic_year': 2023, 'semester': 1, 'score': 80},
        {'sid': 'S_NORMAL', 'academic_year': 2023, 'semester': 2, 'score': 82},
        {'sid': 'S_NORMAL', 'academic_year': 2024, 'semester': 1, 'score': 81},
    ]
    test_db_manager.ingest_records('lms_db', 'activities', activities)

    test_db_manager.run_anomaly_engine()

    student = test_db_manager.execute(
        'sis_db',
        "SELECT current_risk_status, intervention_status FROM students WHERE sid = 'S_NORMAL'",
    )
    assert student[0]['current_risk_status'] == 'Normal'
    assert student[0]['intervention_status'] == 'none'
