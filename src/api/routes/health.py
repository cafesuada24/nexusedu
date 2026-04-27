"""Monitoring and health check routes for the API."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter

from src.database import db_manager

router = APIRouter(tags=['monitoring'])


@router.get('/health')
async def health_check() -> dict[str, Any]:
    """Returns the current status of the API and its dependencies.

    Returns:
        A dictionary containing the status, database health, timestamp, and version.
    """
    db_health = db_manager.check_health()
    all_healthy = all(status == 'healthy' for status in db_health.values())

    return {
        'status': 'online' if all_healthy else 'error',
        'database': db_health,
        'timestamp': datetime.now(UTC).isoformat(),
        'version': '1.0.0',
    }
