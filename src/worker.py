"""ARQ Worker for background job processing."""

from typing import Any

from arq.connections import RedisSettings
from langgraph.checkpoint.memory import MemorySaver

from src.domain.services.agent_metadata import AgentMetadataService
from src.infrastructure.agents.agent import create_graph
from src.infrastructure.database.session import async_session_maker
from src.infrastructure.repositories.sqlalchemy_repositories import (
    SqlAlchemyActivityRepository,
    SqlAlchemyAdvisorRepository,
    SqlAlchemyAlertRepository,
    SqlAlchemyEmailRepository,
    SqlAlchemyIdempotencyRepository,
    SqlAlchemyMetadataRepository,
    SqlAlchemyStatusHistoryRepository,
    SqlAlchemyStudentRepository,
)
from src.presentation.api.services.alerts import AlertService
from src.presentation.api.services.gamification import GamificationService
from src.presentation.api.services.query import QueryService
from src.presentation.api.types import JobStore
from src.telemetry.logger import logger
from src.utils.env import getenv


async def run_email_draft_task(
    _ctx: dict[Any, Any],
    job_id: str,
    sid: str,
    jobs: JobStore,
    booking_link: str | None = None,
    user_id: str | None = None,
) -> None:
    """Worker task to generate email draft."""
    logger.info(f'Worker: Starting email draft task for {sid}')

    async with async_session_maker() as session:
        # Repositories
        student_repo = SqlAlchemyStudentRepository(session)
        advisor_repo = SqlAlchemyAdvisorRepository(session)
        alert_repo = SqlAlchemyAlertRepository(session)
        email_repo = SqlAlchemyEmailRepository(session)
        idempotency_repo = SqlAlchemyIdempotencyRepository(session)

        # Services
        gamification_service = GamificationService(advisor_repo, student_repo)
        alert_service = AlertService(
            alert_repo, email_repo, student_repo, idempotency_repo, gamification_service
        )

        await alert_service.run_email_draft_task(
            job_id=job_id,
            sid=sid,
            jobs=jobs,
            booking_link=booking_link,
            user_id=user_id,
        )


async def run_agent_task(
    _ctx: dict[Any, Any],
    job_id: str,
    query: str,
    thread_id: str | None,
    user_dict: dict[str, Any],
    jobs: JobStore,
) -> None:
    """Worker task to process agent query."""
    logger.info(f'Worker: Starting agent task for {job_id}')

    checkpointer = MemorySaver()
    agent = create_graph(checkpointer=checkpointer)

    async with async_session_maker() as session:
        metadata_repo = SqlAlchemyMetadataRepository(session)
        metadata_service = AgentMetadataService(metadata_repo)
        query_service = QueryService(agent, metadata_service)

        await query_service.run_agent_task(
            job_id=job_id,
            query=query,
            thread_id=thread_id,
            user_dict=user_dict,
            jobs=jobs,
        )


class WorkerSettings:
    """ARQ Worker configuration."""

    functions = [run_email_draft_task, run_agent_task]
    redis_settings = RedisSettings(
        host=getenv('REDIS_HOST', 'localhost'),
        port=int(getenv('REDIS_PORT', '6379')),
    )
