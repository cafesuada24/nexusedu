"""Monitoring and health check routes for the API."""

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from src.api.lifecycle import get_dbmanager
from src.database.manager import DatabaseManager
from src.baml_client import b

router = APIRouter(tags=['monitoring'])


@router.get('/health')
async def health_check(
    db_manager: Annotated[DatabaseManager, Depends(get_dbmanager)],
) -> dict[str, Any]:
    """Returns the current status of the API and its dependencies.

    Returns:
        A dictionary containing the status, database health, AI status, timestamp, and version.
    """
    # Check Database Health
    db_health = db_manager.check_health()
    db_healthy = all(status == 'healthy' for status in db_health.values())

    # Check AI/LLM Status (Basic verification of BAML/connectivity)
    ai_status = "unknown"
    try:
        # We perform a very cheap, minimal call to verify connectivity to the AI provider.
        # This ensures the API key and provider are actually working.
        test_call = b.Respond("Connectivity test. Reply with 'OK'.")
        if test_call:
            ai_status = "healthy"
        else:
            ai_status = "unhealthy: empty response"
    except Exception as e:
        ai_status = f"unhealthy: {e}"

    all_healthy = db_healthy and ai_status == "healthy"

    return {
        'status': 'online' if all_healthy else 'error',
        'database': db_health,
        'ai_layer': ai_status,
        'timestamp': datetime.now(UTC).isoformat(),
        'version': '1.0.0',
    }
