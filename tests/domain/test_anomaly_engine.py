"""Tests for the AnomalyEngine domain service."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.domain.services.anomaly_engine import AnomalyEngine

@pytest.fixture
def mock_repos():
    return {
        'student': MagicMock(),
        'activity': MagicMock(),
        'history': MagicMock()
    }

@pytest.fixture
def engine(mock_repos):
    # Initialize all awaited methods as AsyncMock
    mock_repos['activity'].get_weekly_averages = AsyncMock()
    mock_repos['history'].get_all_history = AsyncMock()
    mock_repos['history'].batch_create_history = AsyncMock()
    mock_repos['history'].get_latest_anomaly = AsyncMock()
    mock_repos['student'].get_by_id = AsyncMock()
    mock_repos['student'].update_risk_status = AsyncMock()
    
    return AnomalyEngine(
        student_repo=mock_repos['student'],
        activity_repo=mock_repos['activity'],
        history_repo=mock_repos['history']
    )

@pytest.mark.asyncio
async def test_run_empty_data(engine, mock_repos):
    """Verify engine handles no data gracefully."""
    mock_repos['activity'].get_weekly_averages.return_value = []
    mock_repos['history'].get_all_history.return_value = []
    
    result = await engine.run()
    assert result == []
    mock_repos['history'].batch_create_history.assert_not_called()

@pytest.mark.asyncio
async def test_run_significant_drop_detection(engine, mock_repos):
    """Verify that a sharp drop in scores triggers an anomaly."""
    # Data: 3 weeks of high scores, then 1 week of low score
    weekly_avgs = [
        {'sid': 'S1', 'avg_score': 90.0, 'academic_year': 2024, 'semester': 1, 'week': 1},
        {'sid': 'S1', 'avg_score': 92.0, 'academic_year': 2024, 'semester': 1, 'week': 2},
        {'sid': 'S1', 'avg_score': 88.0, 'academic_year': 2024, 'semester': 1, 'week': 3},
        {'sid': 'S1', 'avg_score': 40.0, 'academic_year': 2024, 'semester': 1, 'week': 4},
    ]
    mock_repos['activity'].get_weekly_averages.return_value = weekly_avgs
    mock_repos['history'].get_all_history.return_value = []
    mock_repos['history'].get_latest_anomaly.return_value = 'Significant Drop'
    
    # Mock student in 'none' status to allow transition to 'new'
    mock_student = MagicMock()
    mock_student.intervention_status = 'none'
    mock_repos['student'].get_by_id.return_value = mock_student

    result = await engine.run()
    
    assert 'S1' in result
    # Verify history creation
    # Should have 3 records (Week 2, 3, 4) since Week 1 has no previous history for baseline
    args, _ = mock_repos['history'].batch_create_history.call_args
    history_records = args[0]
    assert len(history_records) == 3
    
    # Week 4 should be Significant Drop
    week4_record = next(r for r in history_records if r['week'] == 4)
    assert week4_record['anomaly_flag'] == 'Significant Drop'
    assert week4_record['z_score'] < -1.5

@pytest.mark.asyncio
async def test_run_critical_drop_ratio(engine, mock_repos):
    """Verify that a drop below the critical ratio triggers an anomaly even if baseline variance is low."""
    # Constant high scores, then sudden drop
    weekly_avgs = [
        {'sid': 'S2', 'avg_score': 100.0, 'academic_year': 1, 'semester': 1, 'week': 1},
        {'sid': 'S2', 'avg_score': 100.0, 'academic_year': 1, 'semester': 1, 'week': 2},
        {'sid': 'S2', 'avg_score': 60.0, 'academic_year': 1, 'semester': 1, 'week': 3}, # 0.6 < 0.7 ratio
    ]
    mock_repos['activity'].get_weekly_averages.return_value = weekly_avgs
    mock_repos['history'].get_all_history.return_value = []
    mock_repos['history'].get_latest_anomaly.return_value = 'Critical Drop'
    
    mock_student = MagicMock()
    mock_student.intervention_status = 'none'
    mock_repos['student'].get_by_id.return_value = mock_student

    await engine.run()
    
    args, _ = mock_repos['history'].batch_create_history.call_args
    history_records = args[0]
    week3_record = next(r for r in history_records if r['week'] == 3)
    assert week3_record['anomaly_flag'] == 'Critical Drop'

@pytest.mark.asyncio
async def test_avoid_duplicate_history(engine, mock_repos):
    """Verify that existing history records are not recreated."""
    weekly_avgs = [
        {'sid': 'S1', 'avg_score': 100.0, 'academic_year': 1, 'semester': 1, 'week': 1},
        {'sid': 'S1', 'avg_score': 100.0, 'academic_year': 1, 'semester': 1, 'week': 2},
    ]
    existing_history = [
        {'sid': 'S1', 'academic_year': 1, 'semester': 1, 'week': 2}
    ]
    mock_repos['activity'].get_weekly_averages.return_value = weekly_avgs
    mock_repos['history'].get_all_history.return_value = existing_history
    mock_repos['history'].get_latest_anomaly.return_value = 'Normal'

    await engine.run()
    
    # Should NOT call batch_create_history because the only week with history potential (W2) already exists
    mock_repos['history'].batch_create_history.assert_not_called()

@pytest.mark.asyncio
async def test_no_transition_if_already_in_intervention(engine, mock_repos):
    """Verify student isn't marked as 'new' if already in 'sent' or 'booked' status."""
    weekly_avgs = [
        {'sid': 'S1', 'avg_score': 90.0, 'academic_year': 1, 'semester': 1, 'week': 1},
        {'sid': 'S1', 'avg_score': 40.0, 'academic_year': 1, 'semester': 1, 'week': 2},
    ]
    mock_repos['activity'].get_weekly_averages.return_value = weekly_avgs
    mock_repos['history'].get_all_history.return_value = []
    mock_repos['history'].get_latest_anomaly.return_value = 'Critical Drop'
    
    # Student already in 'sent'
    mock_student = MagicMock()
    mock_student.intervention_status = 'sent'
    mock_repos['student'].get_by_id.return_value = mock_student

    result = await engine.run()
    
    assert result == [] # No NEW transitions
    # But risk status should still be updated
    mock_repos['student'].update_risk_status.assert_called_with('S1', risk_status='Critical Drop')
