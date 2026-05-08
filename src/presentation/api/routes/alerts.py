"""API routes for Kanban Alert Dashboard management."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from src.application.queries.alert_queries import (
    AlertQueryHandler,
    GetActiveAlertsQuery,
)
from src.core.logger import logger
from src.domain.value_objects.status import InterventionStatus
from src.presentation.api.auth import Scope, User, require_scope
from src.presentation.dependencies.providers import (
    get_alert_query_handler,
)
from src.presentation.dtos.pagination import PagedResponse

router = APIRouter(prefix='/alerts', tags=['alerts'])


@router.get('')
async def get_alerts(
    query_handler: Annotated[AlertQueryHandler, Depends(get_alert_query_handler)],
    _: Annotated[User, Depends(require_scope(Scope.ALERTS_READ))],
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Retrieve students who have an active alert for the Kanban board."""
    if status:
        try:
            InterventionStatus(status)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail='Invalid status filter. Must be a valid InterventionStatus.',
            ) from e

    try:
        query = GetActiveAlertsQuery(status_filter=status, limit=limit, offset=offset)
        paged_dto = await query_handler.handle_get_active_alerts(query)

        return {
            'items': [
                {
                    'sid': str(d.student.sid),
                    'student_name': d.student.student_name,
                    'email': d.student.email,
                    'current_risk_status': d.student.current_risk_status.value,
                    'intervention_status': d.student.intervention_status.value,
                    'is_generating': d.student.is_generating,
                    'active_case_id': str(d.student.active_case_id)
                    if d.student.active_case_id
                    else None,
                    'assigned_advisor_id': str(d.student.assigned_advisor_id)
                    if d.student.assigned_advisor_id
                    else None,
                    'assigned_to': d.student.assigned_to,
                }
                for d in paged_dto.items
            ],
            'metadata': {
                'total_count': paged_dto.metadata.total_count,
                'limit': paged_dto.metadata.limit,
                'offset': paged_dto.metadata.offset,
                'has_next': paged_dto.metadata.has_next,
            },
        }
    except Exception as e:
        logger.error(f'Error in get_alerts: {str(e)}', exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
