"""API routes for administrative operations."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.admin_dashboard_dtos import (
    AdminDashboardDTO,
    AdvisorAdminMetricsResponseDTO,
)
from src.application.queries.admin_dashboard_queries import AdminDashboardQueryService
from src.infrastructure.database.session import get_async_session
from src.presentation.api.auth import Scope, require_scope

router = APIRouter(prefix='/admin', tags=['Admin'])


async def get_admin_dashboard_query_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AdminDashboardQueryService:
    """Dependency for AdminDashboardQueryService."""
    return AdminDashboardQueryService(session)


@router.get(
    '/dashboard',
    response_model=AdminDashboardDTO,
    summary='Get school-wide metrics for administrators.',
)
async def get_admin_dashboard(
    query_service: Annotated[
        AdminDashboardQueryService,
        Depends(get_admin_dashboard_query_service),
    ],
    _: Annotated[None, Depends(require_scope(Scope.ADMIN_DASHBOARD))],
) -> AdminDashboardDTO:
    """Returns aggregated metrics for the intervention system."""
    return await query_service.get_dashboard_data()


@router.get(
    '/advisors/metrics',
    response_model=AdvisorAdminMetricsResponseDTO,
    summary='Get detailed performance metrics for all advisors.',
)
async def get_advisor_metrics(
    query_service: Annotated[
        AdminDashboardQueryService,
        Depends(get_admin_dashboard_query_service),
    ],
    _: Annotated[None, Depends(require_scope(Scope.ADMIN_DASHBOARD))],
) -> AdvisorAdminMetricsResponseDTO:
    """Returns a list of advisors with their respective performance metrics."""
    return await query_service.get_advisor_performance_metrics()
