"""Monitoring and health check routes for the API."""

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from src.api.lifecycle import get_dbmanager
from src.baml_client import b
from src.database.manager import DatabaseManager

router = APIRouter(tags=['monitoring'])


@router.get('/health')
async def health_check(
    db_manager: Annotated[DatabaseManager, Depends(get_dbmanager)],
) -> dict[str, Any]:
    """Provides the operational status of the API and its core dependencies.

    Args:
        db_manager: The database manager dependency.

    Returns:
        A dictionary containing the status of various system components.
    """
    # 1. Check SIS/LMS Database Health
    db_health = db_manager.check_health()
    db_healthy = all(status == 'healthy' for status in db_health.values())

    # 2. Check AI Connectivity (BAML/LLM)
    try:
        # This ensures the API key and provider are actually working.
        test_call = b.Respond("Connectivity test. Reply with 'OK'.")
        ai_status = 'healthy' if test_call else 'unhealthy: empty response'
    except Exception as e:
        ai_status = f'unhealthy: {e}'

    all_healthy = db_healthy and ai_status == 'healthy'

    return {
        'status': 'operational' if all_healthy else 'degraded',
        'timestamp': datetime.now(UTC).isoformat(),
        'dependencies': {
            'database': db_health,
            'ai_engine': ai_status,
        },
        'version': '1.0.0',
    }
