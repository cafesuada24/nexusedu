"""ARQ Worker for background job processing."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from arq.connections import RedisSettings
from langgraph.checkpoint.memory import MemorySaver

from src.application.commands.agent_commands import AgentCommandHandler
from src.application.commands.case_commands import (
    CaseCommandHandler,
    GenerateEmailDraftCommand,
)
from src.application.dtos.agent_dtos import AgentResponseDTO, RunAgentTaskCommand
from src.application.services.agent_metadata import AgentMetadataService
from src.core.config import config
from src.core.logger import logger
from src.domain.services.gamification import GamificationService
from src.infrastructure.agents.agent import create_graph
from src.infrastructure.database.session import async_session_maker, get_async_session
from src.infrastructure.extern.baml_drafting_service import BamlEmailDraftingService
from src.infrastructure.persistance.query_services.point_ledger_query_service import (
    SqlAlchemyPointLedgerQueryService,
)
from src.infrastructure.persistance.repositories.sqlalchemy_repositories import (
    SqlAlchemyAdvisorRepository,
    SqlAlchemyBadgeRepository,
    SqlAlchemyCaseRepository,
    SqlAlchemyEmailRepository,
    SqlAlchemyIdempotencyRepository,
    SqlAlchemyJobRepository,
    SqlAlchemyMetadataRepository,
    SqlAlchemyStudentRepository,
)
from src.infrastructure.queue.arq_adapter import ArqTaskQueueAdapter


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
        job_repo = SqlAlchemyJobRepository(session)
        job = await job_repo.get_by_id(job_id)
        try:
            job.start(start_time)
            await job_repo.save(job)
            await session.commit()

            student_repo = SqlAlchemyStudentRepository(session)
            advisor_repo = SqlAlchemyAdvisorRepository(session)
            case_repo = SqlAlchemyCaseRepository(session)
            email_repo = SqlAlchemyEmailRepository(session)
            point_ledger_query_service = SqlAlchemyPointLedgerQueryService(session)

            # Domain Service
            gamification_service = GamificationService()

            # Task Queue (Adapter for worker context)

            task_queue = ArqTaskQueueAdapter(ctx['redis'])

            # Command Handler
            handler = CaseCommandHandler(
                student_repo=student_repo,
                email_repo=email_repo,
                case_repo=case_repo,
                advisor_repo=advisor_repo,
                job_repo=job_repo,
                gamification_service=gamification_service,
                task_queue=task_queue,
                email_drafting_service=BamlEmailDraftingService(),
                point_ledger_query_service=point_ledger_query_service,
            )

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
        metadata_repo = SqlAlchemyMetadataRepository(session)
        metadata_service = AgentMetadataService(metadata_repo)
        idempotency_repo = SqlAlchemyIdempotencyRepository(session)

        handler = AgentCommandHandler(agent, metadata_service, idempotency_repo)
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
        case_repo = SqlAlchemyCaseRepository(session)
        case = await case_repo.get_by_id(case_id=case_id)
        assert case.assigned_advisor_id is not None
        student_repo = SqlAlchemyStudentRepository(session)
        student = await student_repo.get_by_id(case.sid)

        case.mark_as_sent()

        await case_repo.save(case)

    async for session in get_async_session():
        assert case.assigned_advisor_id is not None
        point_ledger_query_service = SqlAlchemyPointLedgerQueryService(session)
        gamification_service = GamificationService()
        points = gamification_service.calculate_points(
            GamificationService.Action.SEND_EMAIL,
            case.assigned_at,
            student.current_risk_status,
        )
        await point_ledger_query_service.award_points(
            advisor_id=case.assigned_advisor_id,
            case_id=case.case_id,
            action='send_email',
            points=points,
            earned_at=datetime.now(UTC),
        )
    # Mock success


async def run_evaluate_badges_task(ctx: dict[str, Any], advisor_id: str) -> None:
    """Worker task to evaluate and award achievement badges for an advisor."""
    logger.info(f'Worker: Evaluating badges for advisor {advisor_id}')

    async for session in get_async_session():
        try:
            badge_repo = SqlAlchemyBadgeRepository(session)
            stats = await badge_repo.get_advisor_stats(UUID(advisor_id))

            gamification = GamificationService()
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


class WorkerSettings:
    """ARQ Worker configuration."""

    functions = [
        run_email_draft_task,
        run_agent_task,
        run_dispatch_email_task,
        run_evaluate_badges_task,
    ]
    redis_settings = RedisSettings(
        host=config.redis_host,
        port=config.redis_port,
    )
    max_jobs = config.worker_max_jobs
    job_timeout = config.worker_job_timeout_sec
