"""API routes for system-wide metrics and dashboard KPIs."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from src.api.auth import Scope, User, require_scope
from src.api.lifecycle import get_metrics_service
from src.api.services.metrics import MetricsService

router = APIRouter(prefix='/metrics', tags=['metrics'])


@router.get('/stats')
async def get_kpi_stats(
    metrics_service: Annotated[MetricsService, Depends(get_metrics_service)],
    _user: Annotated[User, Depends(require_scope(Scope.ADVISORS_READ))],
) -> dict[str, Any]:
    """Retrieve high-level KPI stats for the dashboard."""
    return await metrics_service.get_kpi_stats()


@router.get('/retention')
async def get_retention_trend(
    metrics_service: Annotated[MetricsService, Depends(get_metrics_service)],
    _user: Annotated[User, Depends(require_scope(Scope.ADVISORS_READ))],
) -> list[dict[str, Any]]:
    """Retrieve retention trend data over time."""
    return await metrics_service.get_retention_trend()
