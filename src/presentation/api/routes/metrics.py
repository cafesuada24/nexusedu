"""API routes for system-wide metrics and dashboard KPIs."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from src.presentation.api.auth import Scope, User, require_scope
from src.presentation.api.services.metrics import MetricsService
from src.presentation.dependencies.providers import get_metrics_service

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
