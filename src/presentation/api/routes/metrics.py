"""API routes for system-wide metrics and dashboard KPIs."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from src.presentation.api.auth import Scope, User, require_scope
from src.application.queries.metrics_queries import MetricsQueryHandler
from src.presentation.api.auth import Scope, User, require_scope
from src.presentation.dependencies.providers import get_metrics_query_handler

router = APIRouter(prefix='/metrics', tags=['metrics'])


@router.get('/stats')
async def get_kpi_stats(
    query_handler: Annotated[MetricsQueryHandler, Depends(get_metrics_query_handler)],
    _user: Annotated[User, Depends(require_scope(Scope.ADVISORS_READ))],
) -> dict[str, Any]:
    """Retrieve high-level KPI stats for the dashboard."""
    dto = await query_handler.handle_get_kpi_stats()
    return {
        'retention_rate': dto.retention_rate,
        'total_interventions': dto.total_interventions,
        'advisor_engagement': dto.advisor_engagement,
        'dropout_rate': dto.dropout_rate,
        'total_students': dto.total_students,
    }


@router.get('/retention')
async def get_retention_trend(
    query_handler: Annotated[MetricsQueryHandler, Depends(get_metrics_query_handler)],
    _user: Annotated[User, Depends(require_scope(Scope.ADVISORS_READ))],
) -> list[dict[str, Any]]:
    """Retrieve retention trend data over time."""
    dtos = await query_handler.handle_get_retention_trend()
    return [
        {
            'month': d.month,
            'baseline': d.baseline,
            'current': d.current,
        }
        for d in dtos
    ]
