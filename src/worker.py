"""ARQ Worker for background job processing."""

from typing import Any

from arq.connections import RedisSettings
from langgraph.checkpoint.memory import MemorySaver

from src.agents.agent import create_graph
from src.api.services.alerts import AlertService
from src.api.services.gamification import GamificationService
from src.api.services.query import QueryService
from src.api.types import JobStore
from src.database.algorithms.zscore import DuckDBZScoreAnomalyAlgorithm
from src.database.engines.duckdb_engine import DuckDBEngine
from src.database.manager import DatabaseManager
from src.database.repositories.advisor_repository import AdvisorRepository
from src.database.repositories.student_repository import StudentRepository
from src.telemetry.logger import logger
from src.utils.env import getenv

# Initialize dependencies for the worker

db_manager = DatabaseManager()
db_manager.initialize(DuckDBEngine(), DuckDBZScoreAnomalyAlgorithm())

advisor_repo = AdvisorRepository(db_manager)
student_repo = StudentRepository(db_manager)

gamification_service = GamificationService(advisor_repo, student_repo)
alert_service = AlertService(db_manager, gamification_service, student_repo)

# Agent setup for worker
checkpointer = MemorySaver()
agent = create_graph(checkpointer=checkpointer)
query_service = QueryService(agent, db_manager)


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
