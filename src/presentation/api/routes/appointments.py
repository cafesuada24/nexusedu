"""API routes for querying appointments."""

from datetime import UTC, date, datetime, time, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.core.logger import logger
from src.domain.repositories.appointment_repository import AppointmentRepository
from src.domain.repositories.case_repository import CaseRepository
from src.domain.value_objects.status import MeetingMethod
from src.presentation.dependencies.providers import (
    get_appointment_repository,
    get_case_repository,
)

router = APIRouter(prefix='/appointments', tags=['appointments'])

VN_TZ = timezone(timedelta(hours=7))


class AppointmentSlotResponse(BaseModel):
    """Public-facing booked-slot record (no PII)."""

    date: str = Field(..., description='Local date in yyyy-MM-dd (Asia/Ho_Chi_Minh).')
    slot: str = Field(..., description='Start time in HH:MM (Asia/Ho_Chi_Minh).')
    meeting_method: MeetingMethod


@router.get('')
async def list_appointments(
    case_repo: Annotated[CaseRepository, Depends(get_case_repository)],
    appointment_repo: Annotated[
        AppointmentRepository,
        Depends(get_appointment_repository),
    ],
    case_id: UUID = Query(
        ...,
        description='Case ID — used to identify the assigned advisor.',
    ),
    from_: date = Query(..., alias='from', description='Inclusive start date.'),
    to: date = Query(..., description='Inclusive end date.'),
) -> list[AppointmentSlotResponse]:
    """List slots already booked for the advisor assigned to this case."""
    try:
        case = await case_repo.find_by_id(case_id)
        if case is None or case.assigned_advisor_id is None:
            return []

        from_dt = datetime.combine(from_, time.min, tzinfo=VN_TZ).astimezone(UTC)
        to_dt = datetime.combine(
            to + timedelta(days=1),
            time.min,
            tzinfo=VN_TZ,
        ).astimezone(UTC)

        appointments = await appointment_repo.list_by_advisor_and_range(
            advisor_id=case.assigned_advisor_id,
            from_dt=from_dt,
            to_dt=to_dt,
        )

        return [
            AppointmentSlotResponse(
                date=a.appointment_time.astimezone(VN_TZ).date().isoformat(),
                slot=a.appointment_time.astimezone(VN_TZ).strftime('%H:%M'),
                meeting_method=a.meeting_method,
            )
            for a in appointments
        ]
    except Exception as e:
        logger.error(f'Error in list_appointments: {e}', exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
