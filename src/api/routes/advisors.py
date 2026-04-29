"""API routes for Advisor management and Leaderboards."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.auth import Scope, User, require_scope
from src.api.lifecycle import get_dbmanager
from src.database.manager import DatabaseManager
from src.telemetry.logger import logger

router = APIRouter(prefix='/advisors', tags=['advisors'])


@router.get('/engagement')
async def get_engagement_metrics(
    db_manager: Annotated[DatabaseManager, Depends(get_dbmanager)],
    _user: Annotated[User, Depends(require_scope(Scope.ADVISORS_READ))],
) -> list[dict[str, Any]]:
    """Retrieve engagement metrics aggregated by major (faculty).

    Returns:
        List of majors and their sent/drafted counts.
    """
    sql = """
        SELECT
            major as faculty,
            COUNT(CASE WHEN intervention_status IN ('sent', 'booked', 'supporting', 'resolved') THEN 1 END) as sent,
            COUNT(CASE WHEN intervention_status = 'new' THEN 1 END) as drafted
        FROM students
        GROUP BY major
        ORDER BY sent DESC
    """

    try:
        results = db_manager.execute('sis_db', sql)
        if results and 'error' in results[0]:
            raise ValueError(results[0]['error'])
        return results
    except Exception as e:
        logger.error(f'Failed to fetch engagement metrics: {e}')
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get('/leaderboard')
async def get_leaderboard(
    db_manager: Annotated[DatabaseManager, Depends(get_dbmanager)],
    _user: Annotated[User, Depends(require_scope(Scope.ADVISORS_READ))],
    time_window: str = Query(
        'all_time',
        pattern='^(weekly|monthly|semester|all_time)$',
    ),
) -> list[dict[str, Any]]:
    """Retrieve the advisor leaderboard based on gamification points.

    Args:
        db_manager: The database manager dependency.
        _user: Authenticated user with read access.
        time_window: The time window for the leaderboard.

    Returns:
        List of advisors and their scores.
    """
    interval_map = {
        'weekly': '7 days',
        'monthly': '30 days',
        'semester': '120 days',  # Simplified semester definition
    }

    where_clause = ''
    param = None
    if time_window != 'all_time':
        param = (interval_map[time_window],)
        where_clause = "WHERE timestamp >= current_timestamp - CAST(? AS INTERVAL)"

    # Aggregate points and join with advisors table for names
    sql = f"""
        SELECT
            l.advisor_id,
            COALESCE(a.name, l.advisor_id) as name,
            SUM(l.points) as total_points,
            COUNT(l.id) as actions_count,
            COUNT(CASE WHEN l.action_type = 'email_sent' THEN 1 END) as sent_count,
            COUNT(CASE WHEN l.action_type = 'student_resolved' THEN 1 END) as resolved_count
        FROM advisor_points_ledger l
        LEFT JOIN advisors a ON l.advisor_id = a.advisor_id
        {where_clause}
        GROUP BY l.advisor_id, a.name
        ORDER BY total_points DESC
    """

    try:
        results = db_manager.execute('sis_db', sql, param)
        if results and 'error' in results[0]:
            raise ValueError(results[0]['error'])
        return results
    except Exception as e:
        logger.error(f'Failed to fetch leaderboard: {e}')
        raise HTTPException(status_code=500, detail=str(e)) from e
