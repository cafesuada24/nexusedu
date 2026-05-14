"""Worker tasks for advisor-related workflows."""

from datetime import time

from src.application.commands.schedule_commands import AddWorkingHoursCommand
from src.infrastructure.workers.framework.context import TaskContext
from src.infrastructure.workers.framework.decorators import worker_task
from src.application.dtos.worker_payloads.case_payloads import AdvisorCreatedPayload
from src.application.dtos.worker_payloads.gamification_payloads import EvaluateBadgesPayload


@worker_task()
async def run_advisor_created_task(
    ctx: TaskContext,
    payload: AdvisorCreatedPayload,
) -> None:
    """Worker task to set default working hours for a new advisor."""
    advisor_id = payload.advisor_id
    ctx.logger.info('handling_advisor_created_event', advisor_id=str(advisor_id))

    async with ctx.uow:
        schedule_handler = ctx.container.get_schedule_command_handler()

        # Monday (0) to Friday (4)
        for day in range(5):
            # Morning session
            morning_cmd = AddWorkingHoursCommand(
                advisor_id=advisor_id,
                day_of_week=day,
                start_time=time(9, 0),
                end_time=time(11, 0),
                timezone='Asia/Ho_Chi_Minh',
            )
            # Afternoon session
            afternoon_cmd = AddWorkingHoursCommand(
                advisor_id=advisor_id,
                day_of_week=day,
                start_time=time(14, 0),
                end_time=time(17, 0),
                timezone='Asia/Ho_Chi_Minh',
            )
            await schedule_handler.handle_add_working_hours(morning_cmd)
            await schedule_handler.handle_add_working_hours(afternoon_cmd)

        await ctx.uow.commit()


@worker_task()
async def run_evaluate_badges_task(
    ctx: TaskContext,
    payload: EvaluateBadgesPayload,
) -> None:
    """Worker task to evaluate and award achievement badges for an advisor."""
    advisor_id = payload.advisor_id
    ctx.logger.info('evaluating_badges_for_advisor', advisor_id=str(advisor_id))

    async with ctx.uow:
        new_badges = await ctx.container.gamification_app_service.evaluate_advisor_badges(
            advisor_id,
        )
        await ctx.uow.commit()

    # Invalidate cache if new badges were awarded
    if new_badges and ctx.redis:
        cache_key = f'advisor_badges:{advisor_id}'
        await ctx.redis.delete(cache_key)
        ctx.logger.info(
            'invalidated_cache_for_advisor',
            advisor_id=str(advisor_id),
            count=len(new_badges),
        )

    ctx.logger.info('badge_evaluation_completed', advisor_id=str(advisor_id))
