"""Monitoring and health check routes for the API."""

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from src.api.lifecycle import get_dbmanager
from src.database.manager import DatabaseManager

router = APIRouter(tags=['monitoring'])


@router.get('/health')
async def health_check(
    db_manager: Annotated[DatabaseManager, Depends(get_dbmanager)],
) -> dict[str, Any]:
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
