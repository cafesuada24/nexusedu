"""Monitoring and health check routes for the API."""

from datetime import datetime

from fastapi import APIRouter

router = APIRouter(tags=["monitoring"])

@router.get("/health")
async def health_check() -> dict[str, str]:
    """Returns the current status of the API.

    Returns:
        A dictionary containing the status, current UTC timestamp, and API version.
    """
    return {
        "status": "online",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
    }
