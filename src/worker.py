"""ARQ Worker for background job processing."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from arq.connections import RedisSettings
from langgraph.checkpoint.memory import MemorySaver

from src.application.commands.case_commands import (
    GenerateEmailDraftCommand,
    SubmitCaseReviewCommand,
)
from src.application.dtos.agent_dtos import AgentResponseDTO, RunAgentTaskCommand
from src.core.config import config
from src.core.container import Container
from src.core.logger import logger
from src.domain.value_objects.student_satisfaction import StudentSatisfaction
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
    header: str,
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
        email_sending_service = container.email_sending_service
        point_ledger_repo = container.point_ledger_repo
        gamification_service = container.gamification_service

        case = await case_repo.get_by_id(case_id=case_id)
        assert case.assigned_advisor_id is not None
        email = await email_repo.get_by_case(case_id)
        student = await student_repo.get_by_id(case.sid)

        # Send actual email
        await email_sending_service.send_email(
            to_email=target_email,
            subject=header,
            body=body,
        )

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
            case.created_at,
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


async def run_student_booked_task(
    _: dict[Any, Any],
    case_id: UUID,
    occurred_at: datetime,
) -> None:
    """Worker task to handle StudentBookedEvent."""
    logger.info(f'Worker: Handling StudentBookedEvent for case {case_id}')

    async for session in get_async_session():
        container = Container(session=session)
        case_repo = container.case_repo
        student_repo = container.student_repo
        point_ledger_repo = container.point_ledger_repo

        case = await case_repo.get_by_id(case_id)
        assert case.assigned_advisor_id is not None
        student = await student_repo.get_by_id(case.sid)

        gamification_service = container.gamification_service
        # For student booking, we bypass action time extra points as requested
        points = gamification_service.calculate_points(
            gamification_service.Action.STUDENT_BOOK,
            None,
            student.current_risk_status,
        )

        ledger = await point_ledger_repo.get_by_advisor_id(case.assigned_advisor_id)
        ledger.award_points(
            case_id=case_id,
            action='student_booked',
            points=points,
            earned_at=occurred_at,
        )
        await point_ledger_repo.save(ledger)
        await session.commit()

    logger.info(f'Worker: Finished StudentBookedEvent for case {case_id}')


async def run_case_resolved_task(
    _: dict[Any, Any],
    case_id: UUID,
    advisor_id: UUID,
    occurred_at: datetime,
    satisfaction: StudentSatisfaction,
    comment: str | None = None,
) -> None:
    """Worker task to handle CaseResolvedEvent."""
    logger.info(
        f'Worker: Handling CaseResolvedEvent for case {case_id} (Satisfaction: {satisfaction})',
    )

    async for session in get_async_session():
        container = Container(session=session)
        case_repo = container.case_repo
        student_repo = container.student_repo
        point_ledger_repo = container.point_ledger_repo

        case = await case_repo.get_by_id(case_id)
        student = await student_repo.get_by_id(case.sid)

        gamification_service = container.gamification_service
        # For resolution, we measure from assignment time
        points = gamification_service.calculate_points(
            gamification_service.Action.RESOLVE_CASE,
            case.assigned_at,
            student.current_risk_status,
            satisfaction=satisfaction,
        )

        ledger = await point_ledger_repo.get_by_advisor_id(advisor_id)
        ledger.award_points(
            case_id=case_id,
            action='resolve_case',
            points=points,
            earned_at=occurred_at,
        )
        await point_ledger_repo.save(ledger)
        await session.commit()

    logger.info(f'Worker: Finished CaseResolvedEvent for case {case_id}')


async def run_case_failed_task(
    _: dict[Any, Any],
    case_id: UUID,
    advisor_id: UUID,
    occurred_at: datetime,
    satisfaction: str | None = None,
    comment: str | None = None,
) -> None:
    """Worker task to handle CaseFailedEvent."""
    logger.info(
        f'Worker: Handling CaseFailedEvent for case {case_id} (Satisfaction: {satisfaction})',
    )

    async for session in get_async_session():
        container = Container(session=session)
        point_ledger_repo = container.point_ledger_repo

        # Per requirement, failed cases award 0 points
        ledger = await point_ledger_repo.get_by_advisor_id(advisor_id)
        ledger.award_points(
            case_id=case_id,
            action='resolve_case_failed',
            points=0,
            earned_at=occurred_at,
        )
        await point_ledger_repo.save(ledger)
        await session.commit()

    logger.info(f'Worker: Finished CaseFailedEvent for case {case_id}')


async def run_case_review_requested_task(
    ctx: dict[Any, Any],
    case_id: UUID,
    advisor_id: UUID,
    occurred_at: datetime,
) -> None:
    """Worker task to handle CaseReviewRequestedEvent."""
    logger.info(f'Worker: Handling CaseReviewRequestedEvent for case {case_id}')

    async for session in get_async_session():
        container = Container(session=session, redis_pool=ctx.get('redis'))
        case_repo = container.case_repo
        student_repo = container.student_repo

        case = await case_repo.get_by_id(case_id)
        student = await student_repo.get_by_id(case.sid)

        # 1. Generate JWT token
        payload = {
            'case_id': str(case_id),
            'exp': datetime.now(UTC) + timedelta(days=7),
            'iat': datetime.now(UTC),
        }
        token = jwt.encode(
            payload, config.jwt_secret or 'insecure_default', algorithm='HS256'
        )

        # 2. Dispatch email (Using existing email dispatch logic as base)
        frontend_url = getattr(config, 'frontend_url', 'http://localhost:3000')
        review_link = f'{frontend_url}/cases/review?token={token}'
        email_body = (
            f'Hi {student.student_name},\n\n'
            f'Your advisor has marked your case as resolved. '
            f'Please take a moment to review the support you received: {review_link}\n\n'
            f'Thank you!'
        )

        await container.task_queue.enqueue(
            'run_dispatch_email_task',
            case_id=case_id,
            header='Review support',
            body=email_body,
            target_email=student.email,
        )

        # 3. Schedule auto-resolution after 7 days
        await container.task_queue.enqueue(
            'run_auto_resolve_case_task',
            case_id=case_id,
            _defer_by=timedelta(days=7),
        )

    logger.info(f'Worker: Finished CaseReviewRequestedEvent for case {case_id}')


async def run_auto_resolve_case_task(
    _: dict[Any, Any],
    case_id: UUID,
) -> None:
    """Task to auto-resolve a case if the student hasn't reviewed it after 7 days."""
    logger.info(f'Worker: Running auto-resolve check for case {case_id}')

    async for session in get_async_session():
        container = Container(session=session)
        case_repo = container.case_repo
        case = await case_repo.get_by_id(case_id)

        if case.intervention_status == 'pending_review':
            logger.info(f'Worker: Auto-resolving case {case_id}')
            handler = container.get_case_command_handler()
            command = SubmitCaseReviewCommand(
                case_id=case_id,
                satisfaction=StudentSatisfaction.NORMAL,
                comment='Auto-resolved after 7 days.',
            )
            await handler.handle_submit_case_review(command)
            await session.commit()
        else:
            logger.info(
                f'Worker: Case {case_id} already finalized, skipping auto-resolve.'
            )


class WorkerSettings:
    """ARQ Worker configuration."""

    functions = [
        run_email_draft_task,
        run_agent_task,
        run_dispatch_email_task,
        run_evaluate_badges_task,
        run_case_accepted_task,
        run_student_booked_task,
        run_case_resolved_task,
        run_case_failed_task,
        run_case_review_requested_task,
        run_auto_resolve_case_task,
    ]
    redis_settings = RedisSettings(
        host=config.redis_host,
        port=config.redis_port,
    )
    max_jobs = config.worker_max_jobs
    job_timeout = config.worker_job_timeout_sec
