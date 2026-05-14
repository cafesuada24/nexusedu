"""Worker tasks for case management."""

from src.application.commands.case_commands import SubmitCaseReviewCommand
from src.application.dtos.worker_payloads.case_payloads import (
    AutoResolveCasePayload,
    CaseReviewRequestedPayload,
)
from src.application.dtos.worker_payloads.gamification_payloads import (
    CaseAcceptedPayload,
    CaseFailedPayload,
    CaseResolvedPayload,
)
from src.domain.value_objects.status import InterventionStatus
from src.domain.value_objects.student_satisfaction import StudentSatisfaction
from src.infrastructure.workers.framework.context import TaskContext
from src.infrastructure.workers.framework.decorators import worker_task


@worker_task()
async def run_case_accepted_task(
    ctx: TaskContext,
    payload: CaseAcceptedPayload,
) -> None:
    """Worker task to handle CaseAcceptedEvent."""
    ctx.logger.info('handling_case_accepted_event', case_id=str(payload.case_id))

    async with ctx.uow:
        case = await ctx.uow.cases.get_by_id(payload.case_id)
        student = await ctx.uow.students.get_by_id(case.sid)

        await ctx.container.gamification_app_service.award_points(
            advisor_id=payload.advisor_id,
            case_id=payload.case_id,
            action=ctx.container.gamification_service.Action.ACCEPT_TASK,
            occurred_at=payload.occurred_at,
            base_timestamp=case.created_at,
            risk_level=student.current_risk_status,
        )
        await ctx.uow.commit()


@worker_task()
async def run_case_resolved_task(
    ctx: TaskContext,
    payload: CaseResolvedPayload,
) -> None:
    """Worker task to handle CaseResolvedEvent."""
    ctx.logger.info('handling_case_resolved_event', case_id=str(payload.case_id))

    async with ctx.uow:
        case = await ctx.uow.cases.get_by_id(payload.case_id)
        student = await ctx.uow.students.get_by_id(case.sid)

        await ctx.container.gamification_app_service.award_points(
            advisor_id=payload.advisor_id,
            case_id=payload.case_id,
            action=ctx.container.gamification_service.Action.RESOLVE_CASE,
            occurred_at=payload.occurred_at,
            base_timestamp=case.assigned_at,
            risk_level=student.current_risk_status,
            satisfaction=payload.satisfaction,
        )
        await ctx.uow.commit()


@worker_task()
async def run_case_failed_task(
    ctx: TaskContext,
    payload: CaseFailedPayload,
) -> None:
    """Worker task to handle CaseFailedEvent."""
    ctx.logger.info('handling_case_failed_event', case_id=str(payload.case_id))

    async with ctx.uow:
        ledger = await ctx.uow.point_ledger.get_by_advisor_id(payload.advisor_id)
        ledger.award_points(
            case_id=payload.case_id,
            action='resolve_case_failed',
            points=0,
            earned_at=payload.occurred_at,
        )
        await ctx.uow.point_ledger.save(ledger)
        await ctx.uow.commit()


@worker_task()
async def run_case_review_requested_task(
    ctx: TaskContext,
    payload: CaseReviewRequestedPayload,
) -> None:
    """Worker task to handle CaseReviewRequestedEvent."""
    await ctx.container.case_app_service.initiate_case_review(
        case_id=payload.case_id,
    )


@worker_task()
async def run_auto_resolve_case_task(
    ctx: TaskContext,
    payload: AutoResolveCasePayload,
) -> None:
    """Task to auto-resolve a case if the student hasn't reviewed it after 7 days."""
    case_id = payload.case_id
    ctx.logger.info('running_auto_resolve_check', case_id=str(case_id))

    case = await ctx.container.case_repo.get_by_id(case_id)

    if case.intervention_status == InterventionStatus.PENDING_REVIEW:
        ctx.logger.info('auto_resolving_case', case_id=str(case_id))
        handler = ctx.container.get_case_command_handler()
        command = SubmitCaseReviewCommand(
            case_id=case_id,
            satisfaction=StudentSatisfaction.NORMAL,
            comment='Auto-resolved after 7 days.',
        )
        await handler.handle_submit_case_review(command)
    else:
        ctx.logger.info('case_already_finalized_skipping_auto_resolve', case_id=str(case_id))
