"""ARQ Worker for background job processing."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from arq.connections import RedisSettings
from langgraph.checkpoint.memory import MemorySaver

from src.application.commands.case_commands import GenerateEmailDraftCommand
from src.application.dtos.agent_dtos import AgentResponseDTO, RunAgentTaskCommand
from src.core.config import config
from src.core.container import Container
from src.core.logger import logger
from src.infrastructure.agents.agent import create_graph
from src.infrastructure.database.session import async_session_maker, get_async_session


async def run_email_draft_task(
    ctx: dict[str, Any],
    case_id: UUID,
    job_id: UUID,
    user_id: UUID,
    booking_link: str | None = None,
) -> None:
    """Worker task to generate email draft using AlertCommandHandler."""
    start_time = datetime.now(UTC)
    logger.info(f'Worker: Starting email draft task for {case_id}')

    async for session in get_async_session():
        container = Container(session=session, redis_pool=ctx.get('redis'))
        job_repo = container.job_repo
        job = await job_repo.get_by_id(job_id)
        try:
            job.start(start_time)
            await job_repo.save(job)
            await session.commit()

            # Command Handler via Container
            handler = container.get_case_command_handler()

            command = GenerateEmailDraftCommand(
                case_id=case_id,
                job_id=job_id,
                booking_link=booking_link,
                user_id=user_id,
            )

            await handler.handle_generate_email_draft(command)

            job.finish(datetime.now(UTC))
            await job_repo.save(job)
            logger.info(
                f'Worker: Email generated job finished sucessfully for case with id {case_id}',
            )
        except Exception as e:
            job.fail(datetime.now(UTC))
            await job_repo.save(job)
            logger.info(
                f'Worker: Email generated job failed for case with id {case_id}, error: {e}',
            )


async def run_agent_task(
    _: dict[Any, Any],
    job_id: str,
    query: str,
    thread_id: str | None,
    user_dict: dict[str, Any],
) -> AgentResponseDTO:
    """Worker task to process agent query using AgentCommandHandler."""
    logger.info(f'Worker: Starting agent task for {job_id}')

    checkpointer = MemorySaver()
    agent = create_graph(checkpointer=checkpointer)

    async with async_session_maker() as session:
        container = Container(session=session, agent=agent)
        handler = container.get_agent_command_handler()

        command = RunAgentTaskCommand(
            job_id=UUID(job_id),
            query=query,
            thread_id=UUID(thread_id) if thread_id else None,
            user_dict=user_dict,
        )

        return await handler.handle_run_agent_task(command)


async def run_dispatch_email_task(
    _: dict[str, Any],
    case_id: UUID,
    body: str,
    target_email: str,
) -> None:
    """Worker task to send an email to the student."""
    logger.info(f'Worker: Dispatching email for case {case_id} to {target_email}')
    # Placeholder for actual external email service integration (e.g. SendGrid, AWS SES)
    logger.info(f'Email body preview: {body[:50]}...')

    async for session in get_async_session():
        container = Container(session=session)
        case_repo = container.case_repo
        student_repo = container.student_repo
        email_repo = container.email_repo
        point_ledger_repo = container.point_ledger_repo
        gamification_service = container.gamification_service

        case = await case_repo.get_by_id(case_id=case_id)
        assert case.assigned_advisor_id is not None
        email = await email_repo.get_by_case(case_id)
        student = await student_repo.get_by_id(case.sid)

        student.last_notified_timestamp = datetime.now(UTC)
        await student_repo.save(student=student)

        email.mark_as_sent()
        case.mark_as_sent()

        await email_repo.save(email)
        await case_repo.save(case)

        points = gamification_service.calculate_points(
            gamification_service.Action.SEND_EMAIL,
            case.assigned_at,
            student.current_risk_status,
        )
        ledger = await point_ledger_repo.get_by_advisor_id(case.assigned_advisor_id)
        ledger.award_points(
            case_id=case.case_id,
            action='send_email',
            points=points,
            earned_at=datetime.now(UTC),
        )
        await point_ledger_repo.save(ledger)
        await session.commit()


async def run_evaluate_badges_task(ctx: dict[str, Any], advisor_id: str) -> None:
    """Worker task to evaluate and award achievement badges for an advisor."""
    logger.info(f'Worker: Evaluating badges for advisor {advisor_id}')

    async for session in get_async_session():
        try:
            container = Container(session=session, redis_pool=ctx.get('redis'))
            badge_repo = container.badge_repo
            stats = await badge_repo.get_advisor_stats(UUID(advisor_id))

            gamification = container.gamification_service
            eligible_badges = gamification.check_badges(stats)
            existing_badges = await badge_repo.get_advisor_badges(UUID(advisor_id))

            any_awarded = False
            for badge in eligible_badges:
                if badge not in existing_badges:
                    await badge_repo.award_badge(UUID(advisor_id), badge)
                    any_awarded = True

            await session.commit()

            # Invalidate cache if a new badge was awarded
            if any_awarded:
                redis = ctx.get('redis')
                if redis:
                    cache_key = f'advisor_badges:{advisor_id}'
                    await redis.delete(cache_key)
                    logger.info(f'Worker: Invalidated cache for advisor {advisor_id}')

            logger.info(f'Worker: Badge evaluation completed for {advisor_id}')
        except Exception as e:
            logger.error(f'Worker: Failed to evaluate badges: {e}')
            raise
        return


async def run_case_accepted_task(
    _: dict[Any, Any],
    case_id: UUID,
    advisor_id: UUID,
    occurred_at: datetime,
) -> None:
    """Worker task to handle CaseAcceptedEvent."""
    logger.info(f'Worker: Handling CaseAcceptedEvent for case {case_id}')

    async for session in get_async_session():
        container = Container(session=session)
        case_repo = container.case_repo
        student_repo = container.student_repo
        point_ledger_repo = container.point_ledger_repo

        case = await case_repo.get_by_id(case_id)
        student = await student_repo.get_by_id(case.sid)

        gamification_service = container.gamification_service
        points = gamification_service.calculate_points(
            gamification_service.Action.ACCEPT_TASK,
            occurred_at,
            student.current_risk_status,
        )

        ledger = await point_ledger_repo.get_by_advisor_id(advisor_id)
        ledger.award_points(
            case_id=case_id,
            action='accept_case',
            points=points,
            earned_at=occurred_at,
        )
        await point_ledger_repo.save(ledger)
        await session.commit()

    logger.info(f'Worker: Finished CaseAcceptedEvent for case {case_id}')


class WorkerSettings:
    """ARQ Worker configuration."""

    functions = [
        run_email_draft_task,
        run_agent_task,
        run_dispatch_email_task,
        run_evaluate_badges_task,
        run_case_accepted_task,
    ]
    redis_settings = RedisSettings(
        host=config.redis_host,
        port=config.redis_port,
    )
    max_jobs = config.worker_max_jobs
    job_timeout = config.worker_job_timeout_sec
