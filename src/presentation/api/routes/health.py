"""Monitoring and health check routes for the API."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter

from src.infrastructure.extern.baml_client import b

router = APIRouter(tags=['monitoring'])


@router.get('/health')
async def health_check() -> dict[str, Any]:
    """Provides the operational status of the API and its core dependencies.

    Returns:
        A dictionary containing the status of various system components.
    """
    # 1. Check AI Connectivity (BAML/LLM)
    try:
        # This ensures the API key and provider are actually working.
        test_call = b.Respond("Connectivity test. Reply with 'OK'.")
        ai_status = 'healthy' if test_call else 'unhealthy: empty response'
    except Exception as e:
        ai_status = f'unhealthy: {e}'

    all_healthy = ai_status == 'healthy'

    return {
        'status': 'operational' if all_healthy else 'degraded',
        'timestamp': datetime.now(UTC).isoformat(),
        'dependencies': {
            'ai_engine': ai_status,
        },
        'version': '1.0.0',
    }
