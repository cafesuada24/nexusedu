"""Worker tasks for student-related workflows."""

from src.infrastructure.workers.framework.context import TaskContext
from src.infrastructure.workers.framework.decorators import worker_task
from src.infrastructure.workers.framework.exceptions import NonRetryableTaskError
from src.application.dtos.worker_payloads.gamification_payloads import StudentBookedPayload


@worker_task()
async def run_student_booked_task(
    ctx: TaskContext,
    payload: StudentBookedPayload,
) -> None:
    """Worker task to handle StudentBookedEvent."""
    ctx.logger.info('handling_student_booked_event', case_id=str(payload.case_id))

    async with ctx.uow:
        case = await ctx.uow.cases.get_by_id(payload.case_id)
        if not case.assigned_advisor_id:
            raise NonRetryableTaskError(f"Case {payload.case_id} has no advisor")

        student = await ctx.uow.students.get_by_id(case.sid)

        await ctx.container.gamification_app_service.award_points(
            advisor_id=case.assigned_advisor_id,
            case_id=payload.case_id,
            action=ctx.container.gamification_service.Action.STUDENT_BOOK,
            occurred_at=payload.occurred_at,
            base_timestamp=None,
            risk_level=student.current_risk_status,
        )
        await ctx.uow.commit()
