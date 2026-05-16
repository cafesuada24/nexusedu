"""Worker tasks for AI orchestration."""

from sqlalchemy import select

from src.application.dtos.worker_payloads.ai_payloads import GenerateCaseOverviewPayload
from src.domain.value_objects.status import InterventionStatus
from src.infrastructure.database.models import Case as OrmCase
from src.infrastructure.extern.baml_client.async_client import b
from src.infrastructure.workers.framework.context import TaskContext
from src.infrastructure.workers.framework.decorators import worker_task


@worker_task()
async def run_ai_health_check_task(ctx: TaskContext) -> None:
    """Task to check AI provider health and cache the result in Redis."""
    if not ctx.redis:
        ctx.logger.error('redis_not_found_skipping_ai_health_check')
        return

    try:
        # Call the lightweight health check BAML function
        await b.CheckHealth()
        ai_status = 'healthy'
    except Exception as e:
        ai_status = f'unhealthy: {str(e)}'
        ctx.logger.error('ai_health_check_failed', error=str(e))

    # Cache the result for 5 minutes (300 seconds)
    await ctx.redis.set('ai_health_status', ai_status, ex=300)
    ctx.logger.debug('ai_health_check_status_cached', status=ai_status)


@worker_task()
async def run_batch_case_overviews_task(ctx: TaskContext) -> None:
    """Cron task to trigger AI academic overviews generation for NEW cases (Fan-out)."""
    ctx.logger.info('starting_batch_ai_overview_generation_task')

    # 1. Fetch NEW cases that missing an AI overview
    stmt = select(OrmCase.case_id).where(
        OrmCase.intervention_status == InterventionStatus.NEW,
        OrmCase.academic_summary.is_(None),
    )
    result = await ctx.session.execute(stmt)
    case_ids = [row[0] for row in result.all()]

    if not case_ids:
        ctx.logger.debug('no_new_cases_without_ai_overview_found')
        return

    ctx.logger.info(
        'found_new_cases_for_ai_overview_generation',
        count=len(case_ids),
    )

    # 2. Fan-out: Enqueue individual tasks atomically
    async with ctx.uow:
        for case_id in case_ids:
            await ctx.uow.enqueue(
                'run_generate_case_overview_task',
                payload=GenerateCaseOverviewPayload(case_id=case_id),
            )
        await ctx.uow.commit()

    ctx.logger.info('enqueued_individual_ai_overview_tasks', count=len(case_ids))


@worker_task()
async def run_generate_case_overview_task(
    ctx: TaskContext,
    payload: GenerateCaseOverviewPayload,
) -> None:
    """Worker task to generate AI academic overview for a single case."""
    case_id = payload.case_id
    ctx.logger.info('generating_ai_overview_for_case', case_id=str(case_id))

    case_domain = await ctx.container.case_repo.get_by_id(case_id)
    if not case_domain:
        ctx.logger.error('case_not_found', case_id=str(case_id))
        return

    # 1. Fetch student metrics to provide context to AI
    metrics = await ctx.container.student_query_service.get_student_term_metrics(
        sid=case_domain.sid,
    )

    # 2. Generate overview via BAML
    metrics_context = metrics.model_dump_json()
    overview = await b.GenerateCaseOverview(performance_data=metrics_context)

    # 3. Update the case domain entity
    async with ctx.uow:
        case_domain = await ctx.uow.cases.get_by_id(case_id)
        case_domain.set_ai_overview(
            summary=overview.academic_summary,
            keys=overview.action_keys,
        )

        # 4. Persist the change
        await ctx.uow.cases.save(case_domain)
        await ctx.uow.commit()

    ctx.logger.info('ai_overview_generated', case_id=str(case_id))
