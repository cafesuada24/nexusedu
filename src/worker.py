"""ARQ Worker for background job processing."""

import os
from typing import Any
from uuid import UUID

from arq.connections import RedisSettings
from langgraph.checkpoint.memory import MemorySaver

from src.application.commands.agent_commands import AgentCommandHandler
from src.application.commands.alert_commands import (
    AlertCommandHandler,
    GenerateEmailDraftCommand,
)
from src.application.dtos.agent_dtos import AgentResponseDTO, RunAgentTaskCommand
from src.application.services.agent_metadata import AgentMetadataService
from src.domain.services.gamification import GamificationService
from src.infrastructure.agents.agent import create_graph
from src.infrastructure.database.session import async_session_maker
from src.infrastructure.extern.baml_drafting_service import BamlEmailDraftingService
from src.infrastructure.queue.arq_adapter import ArqTaskQueueAdapter
from src.infrastructure.repositories.sqlalchemy_repositories import (
    SqlAlchemyAdvisorRepository,
    SqlAlchemyAlertRepository,
    SqlAlchemyEmailRepository,
    SqlAlchemyIdempotencyRepository,
    SqlAlchemyJobRepository,
    SqlAlchemyMetadataRepository,
    SqlAlchemyStudentRepository,
)
from src.telemetry.logger import logger


async def run_email_draft_task(
    ctx: dict[str, Any],
    sid: str,
    job_id: str,
    booking_link: str | None = None,
    user_id: str | None = None,
) -> None:
    """Worker task to generate email draft using AlertCommandHandler."""
    logger.info(f"Worker: Starting email draft task for {sid}")

    async with async_session_maker() as session:
        # Repositories
        student_repo = SqlAlchemyStudentRepository(session)
        advisor_repo = SqlAlchemyAdvisorRepository(session)
        alert_repo = SqlAlchemyAlertRepository(session)
        email_repo = SqlAlchemyEmailRepository(session)
        job_repo = SqlAlchemyJobRepository(session)
        idempotency_repo = SqlAlchemyIdempotencyRepository(session)

        # Domain Service
        gamification_service = GamificationService()

        # Task Queue (Adapter for worker context)
        from src.infrastructure.queue.arq_adapter import ArqTaskQueueAdapter

        task_queue = ArqTaskQueueAdapter(ctx["redis"])

        # Command Handler
        handler = AlertCommandHandler(
            student_repo=student_repo,
            email_repo=email_repo,
            alert_repo=alert_repo,
            advisor_repo=advisor_repo,
            job_repo=job_repo,
            idempotency_repo=idempotency_repo,
            gamification_service=gamification_service,
            task_queue=task_queue,
            email_drafting_service=BamlEmailDraftingService(),
        )

        command = GenerateEmailDraftCommand(
            sid=UUID(sid),
            job_id=UUID(job_id),
            booking_link=booking_link,
            user_id=UUID(user_id) if user_id else None,
        )

        result = await handler.handle_generate_email_draft(command)
        await session.commit()
        return result


async def run_agent_task(
    _ctx: dict[Any, Any],
    job_id: str,
    query: str,
    thread_id: str | None,
    user_dict: dict[str, Any],
) -> AgentResponseDTO:
    """Worker task to process agent query using AgentCommandHandler."""
    logger.info(f"Worker: Starting agent task for {job_id}")

    checkpointer = MemorySaver()
    agent = create_graph(checkpointer=checkpointer)

    async with async_session_maker() as session:
        metadata_repo = SqlAlchemyMetadataRepository(session)
        metadata_service = AgentMetadataService(metadata_repo)

        handler = AgentCommandHandler(agent, metadata_service)
        command = RunAgentTaskCommand(
            job_id=UUID(job_id),
            query=query,
            thread_id=UUID(thread_id) if thread_id else None,
            user_dict=user_dict,
        )

        return await handler.handle_run_agent_task(command)


class WorkerSettings:
    """ARQ Worker configuration."""

    functions = [run_email_draft_task, run_agent_task]
    redis_settings = RedisSettings(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
    )
    # Global concurrency limit
    max_jobs = int(os.getenv("WORKER_MAX_JOBS", "5"))
    # Default job timeout in seconds
    job_timeout = int(os.getenv("WORKER_JOB_TIMEOUT", "60"))
