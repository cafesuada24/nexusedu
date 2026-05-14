"""Worker tasks for email workflows."""

from src.application.commands.case_commands import GenerateEmailDraftCommand
from src.application.dtos.worker_payloads.email_payloads import (
    DispatchEmailPayload,
    DispatchReviewEmailPayload,
    EmailDraftPayload,
)
from src.infrastructure.workers.framework.context import TaskContext
from src.infrastructure.workers.framework.decorators import worker_task


@worker_task(track_job=True)
async def run_email_draft_task(
    ctx: TaskContext,
    payload: EmailDraftPayload,
) -> None:
    """Worker task to generate email draft."""
    ctx.logger.info('starting_email_draft_task', case_id=str(payload.case_id))

    handler = ctx.container.get_case_command_handler()
    command = GenerateEmailDraftCommand(
        case_id=payload.case_id,
        job_id=payload.job_id,
        user_id=payload.user_id,
    )

    await handler.handle_generate_email_draft(command)
    ctx.logger.info('email_draft_finished', case_id=str(payload.case_id))


@worker_task(track_job=True)
async def run_dispatch_email_task(
    ctx: TaskContext,
    payload: DispatchEmailPayload,
) -> None:
    """Worker task to send an intervention email to the student."""
    await ctx.container.email_app_service.send_intervention_email(
        case_id=payload.case_id,
        job_id=payload.job_id,
        user_id=payload.user_id,
    )


@worker_task()
async def run_dispatch_review_email_task(
    ctx: TaskContext,
    payload: DispatchReviewEmailPayload,
) -> None:
    """Worker task to send a review email to the student."""
    await ctx.container.email_app_service.send_review_email(
        target_email=payload.target_email,
        subject=payload.header,
        body=payload.body,
    )
